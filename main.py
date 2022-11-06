from statistics import median
from requests import get
from time import sleep
from math import log, sqrt
from pprint import pprint


class Game:
    def __init__(self, id, name, abbreviation):
        self.id = id
        self.name = name 
        self.abbreviation = abbreviation
        self.categories = []
        self.runs = []
        self.runners = []

    def __str__(self):
        return self.name

    def getGameWeight(self):
        if len(self.runs) == 0:
            return 0
        #self.cleanCategories()
        return log(len(self.runners), 10) * 100 #/ sqrt(len(self.categories))

    def cleanCategories(self):
        for category in self.categories:
            if len(category.runs) == 0:
                self.categories.remove(category)



class Category:
    def __init__(self, id, name, variables, game: Game):
        self.id = id
        self.name = name 
        self.variables = variables
        self.game = game
        self.runs = []
        self.runners = []

    def __str__(self):
        return self.name

    def getCatWeight(self):
        if len(self.runs) == 0:
            return 0
        runTimes = []
        for run in self.runs:
            runTimes.append(run.time)
        med = median(runTimes)
        if 'Lowcast' in self.name:
            med /= 30
        return log(med, 3600) * self.game.getGameWeight()
    
    def printPP(self):
        print(self.name, ': ', self.game.getGameWeight(),  self.getCatWeight(), self.getCatWeight()/self.game.getGameWeight())
        if len(self.runs) > 0:
            print(self.runs[0].getRunWeight())



class Run:
    def __init__(self, id, runners, time, position, category: Category):
        self.id = id
        self.runners = runners 
        self.time = time      
        self.position = position
        self.category = category 
        self.game = self.category.game
        self.game.runs.append(self)
        self.category.runs.append(self)
        for runner in self.runners:
            runner.runs.append(self)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.getRunWeight() == other.getRunWeight()

    def __gt__(self, other):
        return self.getRunWeight() > other.getRunWeight()
      
    def getRunWeight(self):
        if self.category.getCatWeight() == 0 or self.position == 0:
            return 0
        return sqrt(len(self.category.runs)/(self.position + len(self.category.runs)*0.05)) * self.category.getCatWeight()



class Runner:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.runs = []
        self.score = 0
        self.multiplier = 0.9

    def __str__(self):
        return self.name

    def totalPP(self):
        self.sortRunsByPP()
        total = 0
        multi = 1
        uniqueCoops = []
        for run in self.runs:
            if len(run.runners) > 1:
                if run.category in uniqueCoops:
                    self.runs.remove(run)
                    continue
                uniqueCoops.append(run.category)
            total += run.getRunWeight() * multi
            multi *= self.multiplier
        return total

    def printPP(self):
        for run in self.runs:
            print(run.category.name, end=': ')
            print(run.getRunWeight())
    
    def sortRunsByPP(self):
        runsSort = []
        runsList = []
        for run in self.runs:
            runsSort.append((run.getRunWeight(), run))
        runsSort.sort(reverse=True)
        for run in runsSort:
            runsList.append(run[1])
        self.runs = runsList

    def writePP(self, total, position):
        line1 = '%d|%s|%d|%d' % (position, self.name, len(self.runs), int(total))
        line2 = '|||'
        weigth = 1
        for run in self.runs:
            score = run.getRunWeight()
            line1 += '|%s||' % (run.category.name)
            line2 += '|%.2f|%.4f|%.2f' % (score, weigth, score * weigth)   
            weigth *= self.multiplier
        line1 += '\n'
        line2 += '\n'
        rankingcsv.write(line1)
        rankingcsv.write(line2)



series = 'harrypotter'     #harrypotter harry_the_hamster
games = {}
players = {}

rankingcsv = open('ranking.csv', 'w')
rankingcsv.write('\n\n')

getSeries = get('https://www.speedrun.com/api/v1/series/%s/games?_bulk=yes' % (series)).json()['data']

for game in getSeries:
    gameName = game['names']['international']
    gameID = game['id']
    games[gameID] = Game(gameID, gameName, game['abbreviation'])
    getCategories = get('https://www.speedrun.com/api/v1/games/%s/categories' % (gameID)).json()['data']
    sleep(0.6)
    for category in getCategories:
        if category['type'] == 'per-level':
            continue
        catVars = {}
        catName = gameName + ' ' + category['name']
        catID = category['id']
        getVariables = get('https://www.speedrun.com/api/v1/categories/%s/variables' % (catID)).json()['data']
        sleep(0.6)
        if len(getVariables) > 0:
            variables = []
            values = []
            valuesNames = []
            indexes = []
            for variable in getVariables:
                varID = variable['id']
                valuesNamesElement = []
                if variable['is-subcategory']:
                    variables.append(varID)
                    values.append(list(variable['values']['values']))  
                    for value in variable['values']['values']:
                        valuesNamesElement.append(variable['values']['values'][value]['label'])  
                    valuesNames.append(valuesNamesElement[:])
                    indexes.append(0)
            
            runVars = True
            while runVars:
                varDict = {}
                catName = gameName + ' ' + category['name']
                for i in range(len(indexes)):
                    catName = catName + ', ' + valuesNames[i][indexes[i]]
                    varDict[variables[i]] = values[i][indexes[i]]
                try:
                    indexes[0] += 1
                    for index in range(len(indexes)):
                        if indexes[index] == len(values[index]):
                            indexes[index] = 0
                            indexes[index+1] += 1
                except IndexError:
                    runVars = False
                games[gameID].categories.append(Category(catID, catName, varDict, games[gameID]))
                print(catName)
        
        else:
            print(catName)
            games[gameID].categories.append(Category(catID, catName, {}, games[gameID]))
    
    for category in games[gameID].categories:
        getLeaderboardAPI = 'https://www.speedrun.com/api/v1/leaderboards/%s/category/%s?' % (gameID, category.id)
        for var in category.variables:
            getLeaderboardAPI +=  "var-%s=%s&" % (var, category.variables[var])
        getLeaderboard = get(getLeaderboardAPI).json()['data']['runs']
        sleep(0.6)
        for runOnBoard in getLeaderboard:
            runRunners = []
            for runner in runOnBoard['run']['players']:
                if runner['rel'] == 'user':
                    runnerID = runner['id']
                    if runnerID not in players:
                        runnerName = get(runner['uri']).json()['data']['names']['international']
                        sleep(0.6)
                        players[runnerID] = Runner(runnerID, runnerName)
                    if players[runnerID] not in games[gameID].runners:
                        category.game.runners.append(players[runnerID])
                    if players[runnerID] not in category.runners:
                        category.runners.append(players[runnerID])
                    runRunners.append(players[runnerID])
            thisRun = Run(runOnBoard['run']['id'], runRunners, runOnBoard['run']['times']['primary_t'], runOnBoard['place'], category)
                    #category.game.runs.append(thisRun)
                    #category.runs.append(thisRun)
                    #players[runnerID].runs.append(thisRun)
        #category.printPP()


#allRunners = {}
#for player in players:
#    allRunners[players[player].id] = players[player].totalPP()
#allRunners = sorted(allRunners.items(), key=lambda x: x[1], reverse=True)

allRunners = []
for player in players:
    allRunners.append((players[player].totalPP(), players[player].id))
allRunners.sort(reverse=True)

i = 1
for player in allRunners:
    runner = players[player[1]]
    runner.writePP(player[0], i)
    i+=1

rankingcsv.close()
