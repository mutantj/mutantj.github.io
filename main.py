import webapp2
import json
import random
import urllib2
import urllib

from google.appengine.ext import db
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch

MAIN_PAGE_HTML = """\
<html>
  <body>
    <form action="/giphypost" method="post">
      <div><textarea name="content" rows="3" cols="25">giphygame </textarea></div>
      <div><input type="submit" value="giphypost"></div>
    </form>
    <form action="/giphyanswer" method="post">
      <div><textarea name="content" rows="3" cols="25">giphyanswer </textarea></div>
      <div><input type="submit" value="giphyanswer"></div>
    </form>
    <form action="/giphyaddwords" method="post">
      <div><textarea name="content" rows="3" cols="25"></textarea></div>
      <div><input type="submit" value="AddWords"></div>
    </form>
    
    <form action="/reset" method="post">
      <div><input type="submit" value="ResetScores"></div>
    </form>
    <form action="/getscores" method="post">
      <div><input type="submit" value="GetScores"></div>
    </form>
    <form action="/getcurrentquestion" method="post">
      <div><input type="submit" value="GetQuestion"></div>
    </form>
  </body>
</html>
"""
triggerwordGame = ["giphygame","Gg","gg"]
triggerwordAnswer = ["giphyanswer","ga","Ga"]
pictionaryWords= ["condom", "superman", "tesla", "overweight", "alcohol", "drawing", "dictionary"]
giphyBaseUrl = "http://api.giphy.com"
giphyTranslateEndPoint = "/v1/gifs/translate?s="
giphySearchEndPoint = "/v1/gifs/search?limit=1&q="
giphyAPIKey = "&api_key=dc6zaTOxFJmzC"
giphyOffset = "&offset="
pointsPerAnswer = 100
slackWebHook = '' #removed web hook add your own incoming web hook in slack here

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.write(MAIN_PAGE_HTML)

def RespondWithJSON(self, jsonToRespondWith):
  self.response.headers['Content-Type'] = 'application/json'   
  retobj = {
    'text': jsonToRespondWith
  } 
  self.response.out.write(json.dumps(retobj))

class CurrentQuestion(db.Model):
  answer = db.StringProperty(required=True)
  url = db.StringProperty(required=True)
  points = db.IntegerProperty(required=True)
  live = db.BooleanProperty(indexed=True)
  randomkey = db.StringProperty(required=True)

class UserScores(db.Model):
    username = db.StringProperty(required=True)
    userid = db.StringProperty(required=True)
    score = db.IntegerProperty(required=True)

#High scores are recorded daily
class HighScores(db.Model):
    username = db.StringProperty(required=True)
    userid = db.StringProperty(required=True)
    score = db.IntegerProperty(required=True)

class WordList(db.Model):
    word = db.StringProperty(required=True)
    randomIndex = db.IntegerProperty(required=True)
    category = db.StringProperty(required=False)


class GiphyGame(webapp2.RequestHandler):
    def post(self):
      if self.request.get("trigger_word") in triggerwordGame or self.request.get("content").startswith("giphygame") :
        CreateGame(self)
      if self.request.get("trigger_word") in triggerwordAnswer or self.request.get("content").startswith("giphyanswer") :
        Answer(self)

def CreateGame(self):
  #check the post for "Play" then pass back a giphy
  currentQuestion = GetCurrentQuestion()
  if currentQuestion == None:
    #giphyList = random.sample(pictionaryWords, 1)
    giphyword = FetchGiphyWord ()
    #self.response.write()
    #

    #write this to db that we are looking for this answer
    #create new question
    data = FetchGiphyUrl(giphyword)
    if data != "":
      dataText = "Question worth "+str(pointsPerAnswer)+"\n" + data
      RespondWithJSON(self, dataText )
      randomKey = str(random.random()).replace(".","")
      cq = CurrentQuestion( answer=giphyword, url=data, points=pointsPerAnswer, live=True, randomkey=randomKey)
      cq.put()
      taskqueue.add(name=randomKey, url="/timeout", countdown="45", params={'key': randomKey})
    else:
      RespondWithJSON(self, "data is null from giphy" )
  else:
    RespondWithJSON(self, "There is already a question in play")
  # else :
  #   #updata current question
  
def FetchGiphyWord():
    index = random.randint(0, 1262)
    currentWordQuery = db.GqlQuery( "SELECT * FROM WordList Where randomIndex = :1", index )
    currentWord = currentWordQuery.get()
    if currentWord != None:
        return currentWord.word
    return "ERROR"


def FetchGiphyUrl(giphyword):
  try:
    fullTestUrl = giphyBaseUrl + giphyTranslateEndPoint + giphyword + giphyAPIKey 
    #+ giphyOffset + str(random.randint(0,10))
    
    result = urllib2.urlopen(fullTestUrl)
    html = result.read()
    obj = json.loads(html)
    data = obj["data"]["images"]["fixed_width"]["url"]
    #data = obj["data"]["image_url"]
    # obj, in this case, is a dictionary, a built-in Python type.
    return data

  except urllib2.URLError, e:
      return ""

def SendToSlack(slackdata):

    retobj = {
        'text': slackdata
    } 
    result = urlfetch.fetch(url=slackWebHook,
    payload=json.dumps(retobj),
    method=urlfetch.POST,
    headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return result

def CleanAnswer(dirtyAnswer):
    for startingAnswer in triggerwordAnswer:
        if dirtyAnswer.startswith(startingAnswer):
            return dirtyAnswer.replace(startingAnswer, "", 1).replace(" ", "").lower()
    return "ERROR"

def Answer(self):
  currentQuestion = GetCurrentQuestion()
  if currentQuestion == None:
    RespondWithJSON(self, "No question is live")
  else:
    #get the answer out of content
    content = self.request.get("content")
    if content != "":
      answer = CleanAnswer(content)
      username = "mutantj"
      userid = "666"
    else :
      answer = CleanAnswer(self.request.get("text"))
      username = self.request.get("user_name")
      userid = self.request.get("user_id")

    if answer != "":
      if answer == currentQuestion.answer.lower():
        user = GetUser(username, userid)
        user.score += currentQuestion.points
        user.put()
        currentQuestion.live = False
        currentQuestion.put()
        taskqueue.Queue('default').delete_tasks(taskqueue.Task(name=currentQuestion.randomkey))
        sendToChannel = username + " is Correct, gets "+str(currentQuestion.points)+" points\n\n"
        sendToChannel = sendToChannel + GetUserScores()
        RespondWithJSON(self, sendToChannel)
        
      else :
        user = GetUser(username, userid)
        wrongtext = username +" is Wrong"
        RespondWithJSON(self, wrongtext)
    else:
      RespondWithJSON(self, "Format giphyanswer <answer>")

def GetUserScores():
    userQuery = db.GqlQuery( "SELECT * FROM UserScores" )
    tempUserString = ""
    for user in userQuery:
        tempUserString = tempUserString + user.username + " score:" + str(user.score) + "\n"
    return tempUserString 

def GetCurrentQuestion():
    currentQuestionQuery = db.GqlQuery( "SELECT * FROM CurrentQuestion WHERE live = True" )
    currentQuestion = currentQuestionQuery.get()
    return currentQuestion

def GetUser(username, userid):
    userQuery = db.GqlQuery( "SELECT * FROM UserScores WHERE username = :1 and userid = :2", username, userid )
    user = userQuery.get()
    if user == None:
        return UserScores(username=username, userid=userid, score=0)
    return user

class Timeout(webapp2.RequestHandler):
    def post(self):
        currentQuestion = GetCurrentQuestion()
        randomKey = self.request.get('key')
        if  currentQuestion != None and randomKey == currentQuestion.randomkey:
            currentQuestion.points = currentQuestion.points / 2
            if currentQuestion.points >= 50:
                data = FetchGiphyUrl( currentQuestion.answer )
                randomKey = str(random.random()).replace(".","")
                currentQuestion.randomkey = randomKey
                currentQuestion.url = data
                currentQuestion.put()
                dataText = "Question worth "+str(currentQuestion.points)+"\n" + data
                SendToSlack(dataText)
                taskqueue.add(name=randomKey, url="/timeout", countdown="60", params={'key': randomKey})
            else:
                currentQuestion.live = False
                currentQuestion.put()
                scores = GetUserScores()
                dataText = "Time ran out the answer was: "+ currentQuestion.answer + "\n" + scores
                SendToSlack(dataText)
                

class GiphyResetScores(webapp2.RequestHandler):
    def post(self):
        userQuery = db.GqlQuery( "SELECT * FROM UserScores" )
        for user in userQuery:
            user.score = 0
            user.put()

        self.response.write("Reset scores")

class GiphyGetScores(webapp2.RequestHandler):
    def post(self):
        userQuery = db.GqlQuery( "SELECT * FROM UserScores" )
        self.response.write("scores:")
        for user in userQuery:
            userline = "username = "+user.username + " score = " + str(user.score) +","
            self.response.write(userline)

class GiphyAddWords(webapp2.RequestHandler):
    def post(self):
        content = self.request.get("content")
        wordlist = content.split()
        i = 0
        for word in wordlist:
            w = WordList(word=word, randomIndex=i)
            i += 1
            w.put()

class ShowCurrentQuestion(webapp2.RequestHandler):
    def post(self):
        currentQuestion = GetCurrentQuestion()
        if currentQuestion != None:
            self.response.write(currentQuestion.answer+" "+currentQuestion.url+ " "+ str(currentQuestion.points)) 


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/timeout', Timeout),
    ('/giphypost', GiphyGame),
    ('/giphyanswer', GiphyGame),
    ('/giphyaddwords', GiphyAddWords),
    ('/reset', GiphyResetScores),
    ('/getscores', GiphyGetScores),
    ('/getcurrentquestion', ShowCurrentQuestion)
], debug=True)
