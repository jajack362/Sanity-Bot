class PersonalBestCategory:
    pbList = []

    def __init__(self, bossName, scale):
        self.bossName = bossName
        self.scale = scale

    def getBossName(self):
        return self.bossName

    def getScale(self):
        return self.scale

    def getPbList(self):
        return self.pbList
    
    def addPb(self, pb):
        if pb not in self.pbList:
            self.pbList.append(pb)
    
    def removePb(self, pb):
        if pb in self.pbList:
            self.pbList.remove(pb)
    
    def sort(self):
        self.pbList.sort(key=lambda x: x.getTime())