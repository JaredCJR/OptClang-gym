#!/usr/bin/env python3
import socket
import os
import sys
import fcntl
import time
import numpy as np

class TcpClient():
    SOCKET = None
    init = False
    def getConnectDict(self, path):
        '''
        return Dict[WorkerID] = ["RemoteEnv-ip", "RemoteEnv-port"]
        '''
        Dict = {}
        with open(path, "r") as file:
            # skip the header line
            file.readline()
            for line in file:
                info = line.split(",")
                strippedInfo = []
                for subInfo in info:
                    strippedInfo.append(subInfo.strip())
                Dict[strippedInfo[0]] = [strippedInfo[1], strippedInfo[2]]
            file.close()
        return Dict

    def EstablishTcpConnect(self, IP, Port):
        if self.init == False:
            self.SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.SOCKET.connect((IP, Port))
            self.init = True

    def DestroyTcpConnection(self):
        if self.init == True:
            self.SOCKET.close()
            self.init = False

    def getDefaultEnvConnectInfo(self):
        EnvConnectInfo = os.getenv("LLVM_THESIS_InstrumentHome", "Error")
        if EnvConnectInfo == "Error":
            print("$LLVM_THESIS_InstrumentHome is not defined.", file=sys.stderr)
            sys.exit(1)
        EnvConnectInfo = EnvConnectInfo + "/Connection/EnvConnectInfo"
        return EnvConnectInfo

    def ReadEnvConnectInfo(self, WorkerID):
        """
        return IP(string), Port(number)
        """
        EnvConnectInfo = self.getDefaultEnvConnectInfo()
        EnvConnectDict = self.getConnectDict(EnvConnectInfo)
        return EnvConnectDict[str(WorkerID)][0], int(EnvConnectDict[str(WorkerID)][1])

    def Send(self, WorkerID, Msg):
        """
        input format:
        WorkerID: number
        Msg: string
        """
        if self.init == False:
            IP, Port = self.ReadEnvConnectInfo(WorkerID)
            self.EstablishTcpConnect(IP, Port)
            self.init = True
        Msg = Msg + "\n"
        self.SOCKET.sendall(Msg.encode('utf-8'))

    def Receive(self, WorkerID):
        """
        Always disconnect after receiving.
        return: string
        """
        fragments  = []
        while True:
            chunck = self.SOCKET.recv(1024)
            if not chunck:
                break
            fragments.append(chunck)
        self.DestroyTcpConnection()
        return b"".join(fragments).decode('utf-8')

class Programs():
    def getAvailablePrograms(self):
        """
        return a dict of available "makefile target" in llvm test-suite
        {name:[cpu-cycles-mean, cpu-cycles-sigma]}
        """
        """
        Unwanted programs: Because of the bug in clang 5.0.1, not all of the
        programs in test-suite can apply the target passes. Therefore, we
        need to avoid them manually. This may change with the LLVM progress!
        """
        UnwantedTargets = ["tramp3d-v4", "spirit"]
        loc = os.getenv("LLVM_THESIS_Random_LLVMTestSuiteScript", "Error")
        if loc == "Error":
            sys.exit(1)
        # Due to Intel Meltdown
        # we re-measure the std-cycles, we should use the newer record.
        loc = loc + "/GraphGen/output/newMeasurableStdBenchmarkMeanAndSigma"
        retDict = {}
        with open(loc, "r") as stdFile:
            for line in stdFile:
                LineList = line.split(";")
                name = LineList[0].strip().split("/")[-1]
                if name not in UnwantedTargets:
                    retDict[name] = [LineList[1].split("|")[1].strip(),
                            LineList[2].split("|")[1].strip()]
            stdFile.close()
        return retDict

    def genRandomPasses(self, TotalNum, TargetNum):
        """
        return a string of passes
        """
        FullSet = range(1, TotalNum + 1)
        FullSet = random.sample(FullSet, len(FullSet))
        SubSet = FullSet[:TargetNum]
        retString = ""
        for item in SubSet:
            retString = retString + str(item) + " "
        return retString

class LockMechanism():
    """
    a simple class to provide a locking mechanism cross processes
    """
    def __init__(self):
        self.LockFile = "/tmp/gym-lockfile"
        self.FD = None

    def acquire(self):
        self.FD = open(self.LockFile, "w+")
        # Note: do not close the fd, it will release the lock.
        fcntl.flock(self.FD, fcntl.LOCK_EX)
        self.FD.write(str(os.getpid()))

    def release(self):
        self.FD.seek(0)
        OwnerPid = self.FD.read()
        #print("My pid={}\n".format(os.getpid()))
        #print("Lock pid={}\n".format(OwnerPid))
        if str(os.getpid()) == OwnerPid:
            fcntl.flock(self.FD, fcntl.LOCK_UN)
            self.FD.close()

class Worker():
    def __init__(self):
        self.LockFileLoc = '/tmp/gym-OptClang-WorkerList'

    def hireRemoteWorker(self):
        """
        return an available WorkerID
        Use cross-processes lock to protect the available worker file
        and parse it.
        """
        retWorkerID = ""
        lock = LockMechanism()
        lock.acquire()
        if os.path.exists(self.LockFileLoc):
            # parse and get the first avavilable worker
            lockFile = open(self.LockFileLoc, 'r')
            workers = lockFile.read().split(',')
            workers = list(filter(None, workers)) # remove empty string in list
            retWorkerID = workers[0]
            if not retWorkerID:
                print("Hire worker failed", file=sys.stderr)
            lockFile.close()

            # write back other workers
            lockFile = open(self.LockFileLoc, 'w')
            line = ""
            for ID in workers[1:]:
                line = line + ID + ","
            lockFile.write(line)
            lockFile.close()
        else:
            # first entry, initialize it!
            tcp = TcpClient()
            lockFile = open(self.LockFileLoc, 'w')
            ConDict = tcp.getConnectDict(tcp.getDefaultEnvConnectInfo())
            line = ""
            for ID, Info in ConDict.items():
                if not retWorkerID:
                    retWorkerID = ID
                    continue
                else:
                    line = line + ID + ","
            lockFile.write(line)
            lockFile.close()
        lock.release()
        return retWorkerID

    def freeRemoteWorker(self, WorkerID):
        if os.path.exists(self.LockFileLoc):
            lock = LockMechanism()
            lock.acquire()
            lockFile = open(self.LockFileLoc, 'a')
            info = WorkerID + ","
            lockFile.write(info)
            lockFile.close()
            lock.release()
        else:
            print("Lock file does not exist.", file=sys.stderr)
            sys.exit(1)
    def InfoFactory(self, ProfiledData):
        """
        Input example
Shootout-C++-hash; cpu-cycles | 1051801991; func | main | 0.190; func | __gnu_cxx::hashtable<std::pair<char const* const, int>, char const*, __gnu_cxx::hash<char const*>, std::_Select1st<std::pair<char const* const, int> >, eqstr, std::allocator<int> >::resize  | 0.097

        Return format:
        dict{"TotalCyclesStat": number(int); "FunctionUsageDict":{"function-name": Usage(float)}}
        """
        retDict = {}
        retDict["TotalCyclesStat"] = None
        retDict["FunctionUsageDict"] = {}
        if ProfiledData is None:
            return retDict
        SplitDataList = ProfiledData.split(';')
        for rec in SplitDataList:
            items = rec.split('|')
            if len(items) == 2: #ex. cpu-cycles | 1051801991
                retDict["TotalCyclesStat"] = int(items[1].strip())
            elif len(items) == 3: #ex. func | main | 0.190
                FuncName = items[1].strip()
                if FuncName == '':
                    continue
                FuncUsage = float(items[2].strip())
                retDict["FunctionUsageDict"][FuncName] = FuncUsage
        return retDict

    def FeatureFactory(self, FeaturesStr):
        retDict = {}
        '''
        Upper bound for each feature is 1000.
        ex. for each fuinction:
        atoi @ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        '''
        functionList = FeaturesStr.split('\n')
        for func in functionList:
            funcInfo = func.split('@')
            feaList = []
            for count in funcInfo[1].split(','):
                try:
                    num = int(count.strip())
                    if num > 1000:
                        num = 1000
                    feaList.append(num)
                except:
                    pass
            # make sure all the features are parsed
            assert(len(feaList) == 4176)
            funcName = funcInfo[0].strip()
            if funcName == '':
                continue
            retDict[funcName] = feaList
        return retDict

    def RemoteDoJobOnce(self, Target, Passes, WorkerID):
        """
        retFeatures : string of features
        retStatus :
            1. "Success"
            2. "Failed"
            3. empty string <-- This is caused by Python3 TCP library.
               (May be fixed in newer library version.)
        retProfiled : Profiled info string
        """
        retFeatures = []
        retStatus = ""

        tcp = TcpClient()
        # tell env-daemon to build, verify and run
        runStart = time.perf_counter()
        msg = "target @ {} @ {}".format(Target, Passes)
        tcp.Send(WorkerID=WorkerID, Msg=msg)
        retStatus = tcp.Receive(WorkerID=WorkerID).strip()
        runEnd = time.perf_counter()
        runTime = runEnd - runStart
        '''
        Get data for success run.
        '''
        retProfiled = None
        retFeatures = None
        if retStatus == "Success":
            sendStart = time.perf_counter()
            # get profiled data
            gotProfiled = False
            while retProfiled is None:
                if gotProfiled:
                    print("Retry to get retProfiled")
                tcp.Send(WorkerID=WorkerID, Msg="profiled @ {}".format(Target))
                retProfiled = tcp.Receive(WorkerID=WorkerID).strip()
                gotProfiled = True
            # get features
            gotFeatures = False
            while retFeatures is None:
                if gotFeatures:
                    print("Retry to get retFeatures")
                tcp.Send(WorkerID=WorkerID, Msg="features")
                retFeatures = tcp.Receive(WorkerID=WorkerID).strip()
                gotFeatures = True
            sendEnd = time.perf_counter()
            sendTime = sendEnd - sendStart
            printMsg = "WorkerID: {}; Target: {}; Status: {}; \nPasses= {};\nRun-Time: {}; Send-Time: {};\n".format(WorkerID, Target, retStatus, Passes, runTime, sendTime)
        else:
            printMsg = "\nRunCmd may failed.\n\nWorkerID: {}; Target: {}; Status: {};\nPasses: {}\nRun-Time: {};\n".format(WorkerID, Target, retStatus, Passes, runTime)
        printMsg = printMsg + "--------------------------------------\n"
        print(printMsg)
        '''
        No matter it is successful or failed, free the worker.
        '''
        return retFeatures, retStatus, retProfiled

    def RemoteDoJob(self, Target, Passes):
        """
        return observation, reward, info, isNormalDone

        observation : Dict of instrumented results
            {"function name": [FeatureVectorList]}
            ex. {'kernel_bicg_StrictFP': [vector of features]}
        reward : "Success" or "Failed"
        info : dict
            {'Target': "name", 'FunctionUsageDict': {'main': float}, 'TotalCyclesStat': int}
            ex. {'Target': "Shootout-C++-except",
                 'FunctionUsageDict': {'main': 0.831}, 'TotalCyclesStat': 5936868987}
        """
        isNormalDone = False
        # get remote-worker
        WorkerID = self.hireRemoteWorker()
        retFeatures, retStatus, retInfo = self.RemoteDoJobOnce(Target, Passes, WorkerID)
        # try at most 10 times
        for _ in range(10):
            if not retStatus:
                '''
                Encounter Python3 TCP connection error.
                (This may be fix by newer TCP library.)
                Try again until get meaningful messages.
                '''
                retFeatures, retStatus, retInfo = self.RemoteDoJobOnce(Target, Passes, WorkerID)
                # for the last try
                if retStatus: # may be "Failed"
                    isNormalDone = True
                    break
            if retStatus: # may be "Failed"
                isNormalDone = True
                break
        # free remote-worker
        self.freeRemoteWorker(WorkerID)
        if isNormalDone:
            # if the retStatus is None or "Failed", treat them as the same.
            if retStatus == "Success":
                '''
                The info wrapper
                '''
                retInfo = self.InfoFactory(retInfo)
                retInfo["Target"] = Target
                retFeatures = self.FeatureFactory(retFeatures)
        else:
            retStatus = "CommunicateError"
        return retFeatures, retStatus, retInfo

    def run(self, Target, ActionList):
        """
        return observation(array), reward(1 or -1), info(dict)
        """
        retOb = []
        retReward = None
        retInfo = {}
        # assemble the desired passes-str
        Passes = ""
        for action in ActionList:
            Passes = Passes + str(action) + " "
        retOb, retReward, retInfo = self.RemoteDoJob(Target, Passes)
        #print(retOb.keys())
        #print(retInfo["FunctionUsageDict"].keys())
        if retReward == "Success":
            retReward = 1
        else:
            retReward = -1
        return retOb, retReward, retInfo
