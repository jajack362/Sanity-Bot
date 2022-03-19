class PersonalBestProfile:
    def __init__(self, member):
        self.member = member
        self.pbList = []

    def addPb(self, pb):
        if pb not in self.pbList:
            self.pbList.append(pb)
    
    def removePb(self, pb):
        if pb in self.pbList:
            self.pbList.remove(pb)

    def getPbList(self):
        return self.pbList

    def getMember(self):
        return self.member