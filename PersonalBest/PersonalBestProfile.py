class PersonalBestProfile:
    def __init__(self, member):
        self.member = member
        self.pbList = []
        self.pbPoints = 0

    def addPb(self, pb):
        if pb not in self.pbList:
            self.pbList.append(pb)
            self.updatePoints()
    
    def removePb(self, pb):
        if pb in self.pbList:
            self.pbList.remove(pb)
            self.updatePoints()

    def getPbList(self):
        return self.pbList

    def getMember(self):
        return self.member

    def updatePoints(self):
        self.pbPoints = 0

        for pb in self.pbList:
            self.pbPoints += pb.getDiaryPoints()

    def getPoints(self):
        return self.pbPoints