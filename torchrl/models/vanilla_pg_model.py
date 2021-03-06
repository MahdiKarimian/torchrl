import torch
import torch.nn.functional as F

import torchrl.utils as U
from torchrl.models import BasePGModel


class VanillaPGModel(BasePGModel):
    '''
    The classical Policy Gradient algorithm.
    '''

    @property
    def batch_keys(self):
        return ['state_t', 'action', 'advantage']

    @property
    def entropy(self):
        return self.memory.dists.entropy().mean()

    def register_losses(self):
        self.register_loss(self.pg_loss)
        self.register_loss(self.entropy_loss)

    def register_callbacks(self):
        super().register_callbacks()
        self.callbacks.register_on_train_start(self.add_dist)

    def add_dist(self, batch):
        parameters = self.forward(batch.state_t)
        self.memory.dists = self.create_dist(parameters)

    def pg_loss(self, batch):
        '''
        Compute loss based on the policy gradient theorem.

        Parameters
        ----------
        batch: Batch
            The batch should contain all the information necessary
            to compute the gradients.
        '''
        log_prob = self.memory.dists.log_prob(batch.action).sum(-1)
        objective = log_prob * batch.advantage
        loss = -objective.mean()

        return loss
