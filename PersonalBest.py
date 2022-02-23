class PersonalBest:
    def __init__(self, submitter, bossName, bossGuess, players, time, proof, timeoutTime, status, messageID, scale):
        self.submitter = submitter
        self.bossName = bossName
        self.bossGuess = bossGuess
        self.players = players
        self.time = time
        self.proof = proof
        self.timeoutTime = timeoutTime
        self.status = status
        self.messageID = messageID
        self.scale = scale

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

    def asString(self):
        return "Boss Name: " + str(self.bossName.value) + ", Players: " + str(self.players) + ", Time: " + str(self.time) + ", Proof: " + str(self.proof)