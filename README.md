# mutantj.github.io

My Second 24h jam. I wanted to learn how to make something with Googles App Engine. 
Rather then just make something boring I had a game idea.

The idea was to create a game with Slack as the chat/multiplayer portion of the game and giphy as the content provider. 
So you could request a "random" animated gif and then guess with your workmates to figure out what that gif was portraying.

My blog explains better how this came about and for what purpose.

http://mutant-j.blogspot.ca/p/giphionary.html

    ('/', MainPage), #this is the test harness
    ('/timeout', Timeout), #when the timeout task finishes this gets called
    ('/giphypost', GiphyGame), #this is the url that Slack hits
    
    ('/giphyanswer', GiphyGame), #for the test harness 
    ('/giphyaddwords', GiphyAddWords),  #for the test harness 
    ('/reset', GiphyResetScores),  #for the test harness 
    ('/getscores', GiphyGetScores),  #for the test harness 
    ('/getcurrentquestion', ShowCurrentQuestion)  #for the test harness 

