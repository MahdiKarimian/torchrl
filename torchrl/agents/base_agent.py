import numpy as np
from abc import ABC, abstractmethod

import torchrl.utils as U


class BaseAgent(ABC):
    '''
    Basic TorchRL agent. Encapsulate an environment and a model.

    Parameters
    ----------
    env: torchrl.envs
        A ``torchrl.envs`` instance.
    model: torchrl.models
        A ``torchrl.models`` instance.
    '''
    _model = None

    def __init__(self, env, model=None, gamma=0.99):
        self.env = env
        self.model = model or self._model
        self.gamma = gamma
        self.logger = U.Logger()
        self.last_logged_ep = self.env.num_episodes

    def _check_termination(self):
        if (self.model.num_updates // self.max_updates >= 1
                or self.env.num_episodes // self.max_episodes >= 1
                or self.env.num_steps // self.max_steps >= 1):
            return True

        return False

    @abstractmethod
    def train(self, max_updates=-1, max_episodes=-1, max_steps=-1):
        '''
        This method should be overwritten by a subclass.

        It should define the training loop of the algorithm.

        Parameters
        ----------
        max_updates: int
            Maximum number of gradient updates (Default is -1, meaning it doesn't matter).
        max_episodes: int
            Maximum number of episodes (Default is -1, meaning it doesn't matter).
        max_steps: int
            Maximum number of steps (Default is -1, meaning it doesn't matter).
        '''
        self.max_updates = max_updates
        self.max_episodes = max_episodes
        self.max_steps = max_steps

    def select_action(self, state):
        '''
        Receive a state and use the model to select an action.

        Parameters
        ----------
        state: numpy.ndarray
            The environment state.

        Returns
        -------
        action: int or numpy.ndarray
            The selected action.
        '''
        return self.model.select_action(state[None])

    def run_one_episode(self):
        '''
        Run an entire episode using the current model.

        Returns
        -------
        batch: dict
            Dictionary containing information about the episode.
        '''
        return self.env.run_one_episode(select_action_fn=self.select_action)

    # TODO: doc
    def write_logs(self):
        new_eps = abs(self.last_logged_ep - self.env.num_episodes)
        self.last_logged_ep = self.env.num_episodes
        rewards = self.env.rewards[-new_eps:]

        self.logger.add_log('Reward/Episode', np.mean(rewards))

        self.logger.log('Update {} | Episode {} | Step {}'.format(
            self.model.num_updates, self.env.num_episodes, self.env.num_steps))

        self.logger.timeit(self.env.num_steps, max_steps=self.max_steps)

    @classmethod
    def from_config(cls, config, env=None):
        '''
        Create an agent from a configuration object.

        Returns
        -------
        torchrl.agents
            A TorchRL agent.
        '''
        if env is None:
            try:
                env = U.get_obj(config.env.obj)
            except AttributeError:
                raise ValueError('The env must be defined in the config '
                                 'or passed as an argument')

        state_shape = env.state_info['shape']
        action_shape = env.action_info['shape']
        model = cls._model.from_config(config.model, state_shape, action_shape)

        return cls(env, model)

    @classmethod
    def from_file(cls, file_path, env=None):
        '''
        Create an agent from a configuration file.

        Parameters
        ----------
        file_path: str
            Path to the configuration file.

        Returns
        -------
        torchrl.agents
            A TorchRL agent.
        '''
        config = U.Config.load(file_path)

        return cls.from_config(config, env=env)
