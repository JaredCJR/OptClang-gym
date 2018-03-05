#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# core modules
import random
import math
import os
import sys
import fcntl

# 3rd party modules
import gym
import numpy as np
from gym import spaces

# our implementation, you should change the path to your "gym-OptClang" relative path.
sys.path.append(os.path.abspath('/home/jrchang/workspace/gym-OptClang/gym_OptClang/envs'))
import RemoteWorker as rwork

class OptClangEnv(gym.Env):
    """
    Define an environment.
    The environment defines which actions can be taken at which point and
    when the agent receives which reward.
    """
    prog = rwork.Programs()
    AllTargetsDict = prog.getAvailablePrograms()
    def __init__(self):
        self.__version__ = "0.1.0"
        print("OptClangEnv - Version {}".format(self.__version__))

        '''
        Define what the agent can do:
        {0, 1, 2, ..., 33}
        '''
        self.action_space = spaces.Discrete(34)

        '''
        Define the observation: the feature from instrumentation of the passes.
        '''
        FeatureSize = 4176
        low = np.array([0]*FeatureSize)
        high = np.array([65535]*FeatureSize)
        self.observation_space = spaces.Box(low, high, shape=None, dtype=np.uint32)

        '''
        Store what the agent tried
        '''
        self.curr_episode = -1
        self.curr_step = 0
        self.action_episode_memory = []
        self.seed_num = None
        #In out "random" experiment, 9 is the avaerage passes number that performs best.
        #FIXME
        self.expected_passes_num = 9
        self.run_target = ""

        # ClangWorker initialization
        self.Worker = rwork.Worker()

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
                For us,
                dict{"function name": [
                list from instrumentation(If you need np.array, do it by yourself)]}
                Note: the upper bound for each feature,
                      refer to "FeatureFactory" in "RemoteWorker.py"
            reward (float) :
                amount of reward achieved by the previous action. The scale
                varies between environments, but the goal is always to increase
                your total reward.
                Indicating "Success = 1" or "Failed = -1"
                For us, the real rewards must calculate again with info(dict).
            episode_over (bool) :
                whether it's time to reset the environment again. Most (but not
                all) tasks are divided up into well-defined episodes, and done
                being True indicates the episode has terminated. (For example,
                perhaps the pole tipped too far, or you lost your last life.)
            info (dict) :
                dict{"Target": "application or bechmark name";
                     "TotalCyclesStat": number(int);
                     "FunctionUsageDict":{"function-name": Usage(float)};}
        """
        self.curr_step += 1
        '''
        The action from the agent is 0~33.
        However, the clang expected 1~34.
        '''
        action = action + 1
        self.action_episode_memory[self.curr_episode].append(action)

        # Initialize the return value
        ob = []
        reward = None
        info = {}
        done = None
        ob, reward, info = self.Worker.run(self.run_target,
                self.action_episode_memory[self.curr_episode])

        if self.curr_step >= self.expected_passes_num:
            done = True
        else:
            done = False
        return ob, reward, done, info

    def _get_init_ob(self, Target, ActionList):
        """
        return the features from applying empty pass
        """
        ob, reward, info = self.Worker.run(Target=Target, ActionList=ActionList)
        return ob, info

    def _reset(self):
        """
        Reset the state of the environment and returns an initial observation and info.

        Returns
        -------
        observation (object): the initial observation of the space.
        """
        self.action_episode_memory.append([])
        self.curr_episode += 1
        self.curr_step = 0
        random.seed(a=self.seed_num)
        TargetList = sorted(list(self.AllTargetsDict.keys()))
        self.run_target = random.choice(TargetList)
        #self.run_target = "sqlite3" # C++ example: city, consumer-lame, Shootout-C++-except
        return self._get_init_ob(self.run_target, self.action_episode_memory[self.curr_episode])

    def _render(self, mode='human', close=False):
        print("gym-OptClang does not support render()")
        return

    def _seed(self, seed_num):
        self.seed_num = seed_num
        return

