#!/usr/bin/env python
# -*- coding: utf-8 -*-

# core modules
import random
import math

# 3rd party modules
import gym
import numpy as np
from gym import spaces


class OptClangEnv(gym.Env):
    """
    Define an environment.
    The environment defines which actions can be taken at which point and
    when the agent receives which reward.
    """

    def __init__(self):
        self.__version__ = "0.1.0"
        print("OptClangEnv - Version {}".format(self.__version__))

        '''
        Define what the agent can do:
        {0, 1, 2, ..., 33}
        '''
        self.action_space = spaces.Discrete(34)

        '''
        Define the observation: the feature from instrumentation the passes.
        '''
        FeatureSize = 4176
        low = np.array([0]*FeatureSize)
        high = np.array([65535]*FeatureSize)
        self.observation_space = spaces.Box(low, high)

        # Store what the agent tried
        self.curr_episode = -1
        self.applied_passes = 0
        self.action_episode_memory = []

    #TODO
    def _step(self, action):
        """
        The agent takes a step in the environment.

        Parameters
        ----------
        action : int

        Returns
        -------
        ob, reward, episode_over, info : tuple
            ob (object) :
                an environment-specific object representing your observation of
                the environment.
            reward (float) :
                amount of reward achieved by the previous action. The scale
                varies between environments, but the goal is always to increase
                your total reward.
            episode_over (bool) :
                whether it's time to reset the environment again. Most (but not
                all) tasks are divided up into well-defined episodes, and done
                being True indicates the episode has terminated. (For example,
                perhaps the pole tipped too far, or you lost your last life.)
            info (dict) :
                 diagnostic information useful for debugging. It can sometimes
                 be useful for learning (for example, it might contain the raw
                 probabilities behind the environment's last state change).
                 However, official evaluations of your agent are not allowed to
                 use this for learning.
        """
        if self.is_banana_sold:
            raise RuntimeError("Episode is done")
        self.curr_step += 1
        self._take_action(action)
        reward = self._get_reward()
        ob = self._get_state()
        return ob, reward, self.is_banana_sold, {}

    #TODO
    def _take_action(self, action):
        self.action_episode_memory[self.curr_episode].append(action)
        self.price = ((float(self.MAX_PRICE) /
                      (self.action_space.n - 1)) * action)

        chance_to_take = get_chance(self.price)
        banana_is_sold = (random.random() < chance_to_take)

        if banana_is_sold:
            self.is_banana_sold = True

        remaining_steps = self.TOTAL_TIME_STEPS - self.curr_step
        time_is_over = (remaining_steps <= 0)
        throw_away = time_is_over and not self.is_banana_sold
        if throw_away:
            self.is_banana_sold = True  # abuse this a bit
            self.price = 0.0

    #TODO
    def _get_reward(self):
        if self.is_banana_sold:
            return self.price - 1
        else:
            return 0.0

    def _reset(self):
        """
        Reset the state of the environment and returns an initial observation.

        Returns
        -------
        observation (object): the initial observation of the space.
        """
        self.action_episode_memory.append([])
        self.curr_episode = -1
        self.applied_passes = 0
        self.action_episode_memory = []
        return self._get_state()

    def _render(self, mode='human', close=False):
        return

    #TODO
    def _get_state(self):
        """Get the observation."""
        ob = [self.TOTAL_TIME_STEPS - self.curr_step]
        return ob
