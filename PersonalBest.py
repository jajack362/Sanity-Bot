class PersonalBest:
    def __init__(self, submitter, bossName, bossConfirmed, players, time, proof, timeoutTime, approved, messageID):
        self.submitter = submitter
        self.bossName = bossName
        self.bossConfirmed = bossConfirmed
        self.players = players
        self.time = time
        self.proof = proof
        self.timeoutTime = timeoutTime
        self.approved = approved
        self.messageID = messageID

    def getSubmitter(self):
        return self.submitter

    def getBossName(self):
        return self.bossName

    def getBossConfirmed(self):
        return self.bossConfirmed

    def getPlayers(self):
        return self.players

    def getTime(self):
        return self.time

    def getProof(self):
        return self.proof
    
    def getTimeoutTime(self):
        return self.timeoutTime

    def getApproved(self):
        return self.approved

    def getMessageID(self):
        return self.messageID

    def setBossName(self, bossName):
        self.bossName = bossName

    def setBossConfirmed(self, getBossConfirmed):
        self.getBossConfirmed = getBossConfirmed

    def setPlayers(self, players):
        self.players = players

    def setTime(self, time):
        self.time = time

    def setProof(self, proof):
        self.proof = proof

    def setTimeoutTime(self, newTime):
        self.timeoutTime = newTime
    
    def setApproved(self, approved):
        self.approved = approved

    def setMessageID(self, messageID):
        self.messageID = messageID