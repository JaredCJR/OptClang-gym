#!/usr/bin/env python3
import socket
import os
import sys
import fcntl
import time

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
    LockFile = "/tmp/gym-lockfile"
    FreeMsg = "Free"
    FD = None
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
        pass

    def FeatureFactory(self, FeaturesStr):
        retDict = {}
        '''
        ex. for each fuinction:
        atoi @ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        '''
        functionList = FeaturesStr.split('\n')
        for func in functionList:
            funcInfo = func.split('@')
            feaList = []
            for count in funcInfo[1].split(','):
                try:
                    feaList.append(int(count.strip()))
                except:
                    pass
            retDict[funcInfo[0].strip()] = feaList
        print(retDict.keys())
        return retDict

    def RemoteDoJobOnce(self, Target, Passes):
        """
        retFeatures : List of instrumented results
        retStatus :
            1. "Success"
            2. "Failed"
            3. empty string <-- This is caused by Python3 TCP library.
               (May be fixed in newer library version.)
        retInfo : Profiled info dict
        """
        retFeatures = []
        retStatus = ""
        retInfo = {}

        tcp = TcpClient()
        # get remote-worker
        WorkerID = self.hireRemoteWorker()
        # tell env-daemon to build, verify and run
        runStart = time.perf_counter()
        #FIXME: for debugging
        Target="nsieve-bits"
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
            printMsg = "WorkerID: {}; Target: {}; Status: {}; \nProfileSize: {}; FeatureSize: {}; \nRun-Time: {}; Send-Time: {};".format(WorkerID, Target, retStatus, len(retProfiled), len(retFeatures), runTime, sendTime)
        else:
            printMsg = "RunCmd may failed.\nWorkerID: {}; Target: {}; Status: {}; \nRun-Time: {};".format(WorkerID, Target, retStatus, runTime)

        print(printMsg)
        retInfo = self.InfoFactory(retProfiled)
        retFeatures = self.FeatureFactory(retFeatures)
        '''
        No matter it is successful or failed, free the worker.
        '''
        self.freeRemoteWorker(WorkerID)
        return retFeatures, retStatus, retInfo

    def RemoteDoJob(self, Target, Passes):
        retFeatures, retStatus, retInfo = self.RemoteDoJobOnce(Target, Passes)
        while not retStatus:
            '''
            Encounter Python3 TCP connection error.
            (This may be fix by newer TCP library.)
            Try again until get meaningful messages.
            '''
            retFeatures, retStatus, retInfo = self.RemoteDoJobOnce(Target, Passes)
        return retFeatures, retStatus, retInfo

    def run(self, target, OldPasses, action):
        """
        return the result from the remote worker.
        """
        retOb = []
        retReward = None
        retInfo = {}
        return retOb, retReward, retInfo
