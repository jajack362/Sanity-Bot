from PersonalBest.PersonalBestDiaryLevel import PersonalBestDiaryLevel


class PersonalBest:

    def __init__(self, bossName, players, time, proof, scale, submitter = None, bossGuess = None, status = None , timeoutTime = None):
        self.submitter = submitter
        self.bossName = bossName
        self.bossGuess = bossGuess
        self.players = players
        self.time = time
        self.proof = proof
        self.timeoutTime = timeoutTime
        self.status = status
        self.messageID = 0
        self.scale = scale
        self.messagesToDelete = []
        self.messagesToKeep = []
        self.diaryLevel = PersonalBestDiaryLevel.NONE

    def getSubmitter(self):
        return self.submitter

    def getBossName(self):
        return self.bossName

    def getBossGuess(self):
        return self.bossGuess

    def getPlayers(self):
        return self.players

    def getTime(self):
        return self.time

    def getProof(self):
        return self.proof
    
    def getTimeoutTime(self):
        return self.timeoutTime

    def getStatus(self):
        return self.status

    def getMessageID(self):
        return self.messageID
    
    def getScale(self):
        return self.scale

    def setBossName(self, bossName):
        self.bossName = bossName

    def setBossGuess(self, bossGuess):
        self.bossGuess = bossGuess

    def setPlayers(self, players):
        self.players = players

    def setTime(self, time):
        self.time = time

    def setProof(self, proof):
        self.proof = proof

    def setTimeoutTime(self, newTime):
        self.timeoutTime = newTime
    
    def setStatus(self, status):
        self.status = status

    def setMessageID(self, messageID):
        self.messageID = messageID

    def setScale(self, scale):
        self.scale = scale

    def addMessageToDelete(self, message):
        if message not in self.messagesToDelete:
            self.messagesToDelete.append(message)
    
    def getMessagesToDelete(self):
        return self.messagesToDelete

    def addMessageToKeep(self, message):
        if message not in self.messagesToKeep:
            self.messagesToKeep.append(message)
    
    def getMessagesToKeep(self):
        return self.messagesToKeep
    
    def setDiaryLevel(self, diaryLevel):
        self.diaryLevel = diaryLevel
    
    def getDiaryLevel(self):
        return self.diaryLevel

    def asString(self):
        return "Boss Name: " + str(self.bossName.value) + ", Players: " + str(self.players) + ", Time: " + str(self.time) + ", Proof: " + str(self.proof)