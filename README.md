This repository contains a PIP package which is an OpenAI environment for simulating an environment for OptClang.


Installation
---------------------------------------

Install the [OpenAI gym](https://gym.openai.com/docs/).

Then install this package via

```
sudo -H pip3 install -e . --upgrade
```

Usage
---------------------------------------

```
import gym
import gym_OptClang

env = gym.make('OptClang-v0')
```


The Environment
---------------------------------------

- Observation
  - Type: BOX(4176)


| Num  | Observation           | Min | Max                                                                                 |
| ---- | --------------------- | --- | ----------------------------------------------------------------------------------- |
| 0    | Added by PassRewriter | 0   | Maximum number of unsigned int(Based on the instrumentation runtime implementation) |
| …    | …                     | …   | …                                                                                   |
| 4175 | Added by PassRewriter | 0   | Maximum number of unsigned int(Based on the instrumentation runtime implementation) |


- Actions
  - Type: Discrete(34)
  - The action start from “0”, but the modified Clang start from 1


| Num | Action (Apply pass)            |
| --- | ------------------------------ |
| 0   | PGOMemOPSizeOptLegacyPass      |
| 1   | InstructionCombiningPass       |
| 2   | InstructionSimplifierPass      |
| 3   | LowerSwitchPass                |
| 4   | PromoteMemoryToRegisterPass    |
| 5   | BitTrackingDCEPass             |
| 6   | LoopDataPrefetchPass           |
| 7   | ConstantHoistingPass           |
| 8   | SROAPass                       |
| 9   | GVNSinkPass                    |
| 10  | SCCPPass                       |
| 11  | ScalarizerPass                 |
| 12  | JumpThreadingPass              |
| 13  | NaryReassociatePass            |
| 14  | MergedLoadStoreMotionPass      |
| 15  | DeadStoreEliminationPass       |
| 16  | SinkingPass                    |
| 17  | EarlyCSEPass                   |
| 18  | FlattenCFGPass                 |
| 19  | DeadCodeEliminationPass        |
| 20  | DemoteRegisterToMemoryPass     |
| 21  | PlaceSafepointsPass            |
| 22  | AlignmentFromAssumptionsPass   |
| 23  | PartiallyInlineLibCallsPass    |
| 24  | AggressiveDCEPass              |
| 25  | StraightLineStrengthReducePass |
| 26  | GVNPass                        |
| 27  | TailCallEliminationPass        |
| 28  | NewGVNPass                     |
| 29  | GVNHoistPass                   |
| 30  | ConstantPropagationPass        |
| 31  | ReassociatePass                |
| 32  | MemCpyOptPass                  |
| 33  | LowerExpectIntrinsicPass       |


* Reward
    * Calculation based on Function-Dict
        * Return dict{ “function name”: reward }
            * With function usage from profiling:
                *  `alpha * 10 * ((old_total_cycles * old_usage - new_total_cycles * new_usage) / (old_total_cycles * old_usage)) * abs((delta_total_cycles - sigma_total_cycles)/sigma_total_cycles)`
            *  Without function usage from profiling
                *  `alpha * ((old_total_cycles - new_total_cycles) / old_total_cycles) * abs((delta_total_cycles - sigma_total_cycles)/sigma_total_cycles)`


- Starting State
  - Random select a program
- Episode Termination
  - The episode ends after you apply N passes
    - Based on the random results, 9 is good choice
- Solved Requirements
  - As same as the “Episode Termination”
