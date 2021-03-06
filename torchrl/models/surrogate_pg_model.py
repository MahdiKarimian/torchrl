import torch
import torch.nn.functional as F
from torch.distributions.kl import kl_divergence

from torchrl.models import BasePGModel


class SurrogatePGModel(BasePGModel):
    r'''
    The Surrogate Policy Gradient algorithm instead maximizes a "surrogate" objective, given by:

    .. math::

        L^{CPI}({\theta}) = \hat{E}_t \left[\frac{\pi_{\theta}(a|s)}
        {\pi_{\theta_{old}}(a|s)} \hat{A} \right ]

    '''

    # TODO: Fix kl div for adaptive model, need to be calculated every mini-batch
    @property
    def kl_div(self):
        return kl_divergence(self.memory.old_dists, self.memory.new_dists).sum(-1).mean()

    @property
    def entropy(self):
        return self.memory.new_dists.entropy().mean()

    @property
    def batch_keys(self):
        return ['state_t', 'action', 'advantage', 'old_log_prob']

    def register_losses(self):
        self.register_loss(self.surrogate_pg_loss)
        self.register_loss(self.entropy_loss)

    def register_callbacks(self):
        super().register_callbacks()
        self.callbacks.register_on_mini_batch_start(self.add_new_dist)

    def add_new_dist(self, batch):
        parameters = self.forward(batch.state_t)
        self.memory.new_dists = self.create_dist(parameters)
        batch.new_log_prob = self.memory.new_dists.log_prob(batch.action).sum(-1)
        self.memory.prob_ratio = self.calculate_prob_ratio(batch.new_log_prob,
                                                           batch.old_log_prob)

    def train_step(self, batch):
        with torch.no_grad():
            parameters = self.forward(batch.state_t)
            self.memory.old_dists = self.create_dist(parameters)
            batch.old_log_prob = self.memory.old_dists.log_prob(batch.action).sum(-1)

        super().train_step(batch)
        self.add_new_dist(batch)

    def surrogate_pg_loss(self, batch):
        '''
        The surrogate pg loss, as described before.

        Parameters
        ----------
            batch: Batch
        '''
        prob_ratio = self.calculate_prob_ratio(batch.new_log_prob, batch.old_log_prob)
        surrogate = prob_ratio * batch.advantage
        loss = -surrogate.mean()

        return loss

    def calculate_prob_ratio(self, new_log_probs, old_log_probs):
        '''
        Calculates the probability ratio between two policies.

        Parameters
        ----------
        new_log_probs: torch.Tensor
        old_log_probs: torch.Tensor
        '''
        prob_ratio = (new_log_probs - old_log_probs).exp()
        return prob_ratio

    def write_logs(self, batch):
        super().write_logs(batch)
        self.add_log('KL Divergence', self.kl_div, precision=4)
