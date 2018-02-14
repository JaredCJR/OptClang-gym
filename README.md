This repository contains a PIP package which is an OpenAI environment for simulating an environment for OptClang.

gym-OptClang
==============================================================
The `gym-OptClang` is an `OpanAI Gym` compatiable interface.\
However, do not assume the usage of APIs are as same as the `Gym`\
Read the document and source code may help you a lot.


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
    - This is already handled inside `gym-OptClang`


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


- Reward
  - Indictating status
    - Success: 1
    - Fail: -1
  - Real reward calculating based on the returned "Dict" during runtime
    - Please refer to [source code of the agent](https://github.com/JaredCJR/PPO-OptClang) for more details.

- Starting State
  - Random select a program
- Episode Termination
  - The episode ends after you apply N passes
    - Based on the random results, 9 is good choice
- Solved Requirements
  - As same as the “Episode Termination”
