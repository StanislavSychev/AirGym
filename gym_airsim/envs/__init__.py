from gym_airsim.envs.AirGym import AirSimEnv
from gym.envs.registration import registry, register, make, spec
register(
    id='AirSimEnv-v42',
    entry_point='gym_airsim.envs:AirSimEnv',
)
