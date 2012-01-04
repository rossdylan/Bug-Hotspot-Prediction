#!/opt/local/bin/python3.2
import urllib.request
import urllib.parse
import json
import time
import math
from datetime import datetime


def parseGitTimeString(timeString):
	"""take a standard iso timestamp and turn it into posix time"""
	dt = timeString.split("T")
	date = dt[0]
	_time = dt[1]
	#"2011-04-14T16:00:49Z"
	dateElements = date.split('-')
	timeElements = _time.split(':')
	dtObject = datetime(int(dateElements[0]),
			int(dateElements[1]),
			int(dateElements[2]),
			int(timeElements[0]),
			int(timeElements[1]))
	posix = time.mktime(dtObject.timetuple())
	return posix

class gitRepository(object):
	def __init__(self,user,repo,branch=None):
		self.user = user
		self.repo = repo
		self.branch = branch

	def getCommits(self):
		"""Get a list of commits"""
		requestString = "https://api.github.com/repos/{}/{}/commits"
		requestString = requestString.format(self.user,self.repo)
		data = None
		if self.branch != None:
			response = urllib.request.urlopen(requestString,
					data=urllib.parse.urlencode(('sha', self.branch)))
			data = response.read().decode('utf-8')
		else:
			response = urllib.request.urlopen(requestString)
			data = response.read().decode('utf-8')
			data = json.loads(data)
		data = sorted(data,key=lambda item:parseGitTimeString(item['commit']['committer']['date']))
		return data

	def getChangedFilesForCommits(self):
		"""Return a list of files changed for each commit"""
		"""Returns [{'time':time, 'files':[filenames,]}]"""
		requestString = "https://api.github.com/repos/{}/{}/compare"
		requestString = requestString.format(self.user,self.repo)
		commits = self.getCommits()
		changes = []
		for commitIndex in range(len(commits)):
			if commitIndex == 0:
				continue
			else:
				current = commits[commitIndex]['sha']
				previous = commits[commitIndex-1]['sha']
				commitTime = parseGitTimeString(commits[commitIndex]['commit']['committer']['date'])
				print('Comparing: {} - {}'.format(previous,current))
				compareString = "/{}...{}"
				compareString = compareString.format(previous,current)
				tempRequestString = requestString + compareString
				response = urllib.request.urlopen(tempRequestString)
				data = response.read().decode('utf-8')
				data = json.loads(data)
				files = data['files']
				#this right here is wrong... should be commitsha:{time:124523523,files:changed}
				filesChanged = {'time':commitTime, 'files':[file['filename'] for file in files]}
				changes.append(filesChanged)
		return changes

def calculateSingleScore(time):
	"""Calculate a single part of a files score"""
	return 1 / (1 + math.pow(math.e, -12 * (time + 12)))
def predictBugs(commitChanges):
	"""First step is to find our first commit time,
		this becomes our zero point"""
	earliestCommitTime = commitChanges[0]['time']
	latestCommitTime = commitChanges[0]['time']
	for change in commitChanges:
		if change['time'] <= earliestCommitTime:
			earliestCommitTime = change['time']
		if change['time'] >= latestCommitTime:
			latestCommitTime = change['time']

	"""Next we normalize all other commit times using this earliest time"""
	modifiedChanges = []
	for change in commitChanges:
		normTime = (change['time'] - earliestCommitTime) / (math.fabs(earliestCommitTime) + math.fabs(latestCommitTime))
		modifiedChanges.append({'time':normTime,'files':change['files']})
	commitChanges = modifiedChanges
	"""Now we need to calculate each files score"""
	score = {}
	for change in commitChanges:
		for file in change['files']:
			if file in score:
				score[file] += calculateSingleScore(change['time'])
			else:
				score[file] = calculateSingleScore(change['time'])
	return score

def prettyPrintScoreDict(d):
	print("{")
	for key in d:
		print("\t{}: {}".format(key,d[key]))
	print("}")


if __name__ == "__main__":
	repository = gitRepository(input('Username: '),input('Repository: '))
	prettyPrintScoreDict(predictBugs(repository.getChangedFilesForCommits()))
