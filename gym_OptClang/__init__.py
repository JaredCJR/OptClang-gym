import logging
from gym.envs.registration import register

logger = logging.getLogger(__name__)

register(
    id='OptClang-v0',
    entry_point='gym_OptClang.envs:OptClangEnv',
)
