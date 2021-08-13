from flask import Flask, request,jsonify
from firebase_admin import credentials,firestore,initialize_app
from flask_restful import Api, Resource
import scipy
from sentence_transformers import SentenceTransformer
import json
import numpy as np
DATA_REQUEST_GET_QUESTIONS="questions"
DATA_REQUEST_GET_INTERVIEWS="interviews"
DATA_REQUEST_GET_INTERVIEW="interview"
DATA_REQUEST_GET_FEEDBACKS="feedbacks"
INTERVIEW_COLLECTION="interview"
QUESTION_COLLECTION="question"
USER_COLLECTION="user"
FEEDBACK_COLLECTION="feedback"
USER_COLLECTION="user"
interview_scores = []
interview_scores_float=[]

model = SentenceTransformer('bert-base-nli-mean-tokens')
app = Flask(__name__)
api=Api(app)
cred = credentials.Certificate('key.json')
default_app =initialize_app(cred)
db = firestore.client()
data_store = db.collection(QUESTION_COLLECTION)
import requests
class getQuestionsAPI(Resource):
    def post(self):
        return getQuestionsList()
class getInterviewsAPI(Resource):
    def post(self):
        user_id= request.json['user_id']
        return getInterviews(user_id)


class getInterviewAPI(Resource):
    def post(self):
        interview_id = request.json['interview_id']
        return getInterview(interview_id)

class getFeedbacksAPI(Resource):
    def post(self):
        return getFeedbacks(request.json)


api.add_resource(getQuestionsAPI, "/" +DATA_REQUEST_GET_QUESTIONS)
api.add_resource(getInterviewsAPI, "/" +DATA_REQUEST_GET_INTERVIEWS)
api.add_resource(getInterviewAPI, "/" +DATA_REQUEST_GET_INTERVIEW)
api.add_resource(getFeedbacksAPI, "/" +DATA_REQUEST_GET_FEEDBACKS)



@app.route('/questions', methods=['GET','POST'])
def getQuestionsList():
    questions={}
    docs = db.collection(QUESTION_COLLECTION).stream()
    for doc in docs:
        question={doc.id:doc.to_dict()["text"]}
        questions.update(question)
        # questions.append(f'{doc.id} : {doc.to_dict()["text"]}')
    return questions
    # # docs_json=json.dumps(docs)
    # # print(docs_json)
    # return type(docs)

    #
    # dic = {}
    # dic2 = {"d": "f"}
    # dic.update(dic2)
    # print(dic)


@app.route('/interviews', methods=['GET', 'POST'])
def getInterviews(user_id):

    # doc_ref = db.document(u"<google.cloud.firestore_v1.document.DocumentReference object at 0x7f8f220ad821>")
    # print(doc_ref)

    '''
    doc_ref = db.collection("interview")
    for doc in doc_ref.stream():
        print(doc.reference)
    '''
    doc_ref = db.collection(USER_COLLECTION).document(user_id)
    interview_references = doc_ref.get().to_dict()['interviews'] # return a LIST object type has all references
    interviews= getInterviewsList(interview_references)

    return {"interviews": interviews}

def getInterview(interview_id):
    interviews_id=[interview_id]
    return getInterviewsList(interviews_id)



from datetime import datetime

import json
import datetime
from json import JSONEncoder

def getInterviewsList(interview_references):
    interviews=[] #json object
    for interview_reference in interview_references:
        doc_ref= db.collection(INTERVIEW_COLLECTION)
        doc= doc_ref.document(interview_reference)
        interview = doc.get().to_dict() # return interview json object
        interview['interview_questions']= getInterviewQuestions(interview['interview_questions'])
        interview['feedback']=getInterviewFeedbacks(interview['feedback'])
        '''
        take the interview_questions_id from the interview json object and then pass id's to the 
        getInterviewQuestions to return the questions text, then replace the value
         of "interview_questions" in the interview object from the question id's to the question texts
        '''
        interviews.append(interview)

    return interviews



def getInterviewQuestions(interview_questions_ids):
    doc_ref = db.collection(QUESTION_COLLECTION)
    questions=[]
    for interview_questions_id in interview_questions_ids:
         doc= doc_ref.document(str(interview_questions_id))
         questions.append(doc.get().to_dict()['text']) # to get the question and store in the list

    return questions

targeted_skills=[]
def getFeedbacks(request):
    count=0
    for question_id in request["questions_ids"]:
        doc_ref = db.collection(QUESTION_COLLECTION)
        doc = doc_ref.document(str(question_id))
        question= doc.get().to_dict()['text']
        targeted_skills.append(doc.get().to_dict()['soft_skill'])
        # to get the question content from firestore
        perfect_answers= doc.get().to_dict()['answer']
        # to get the perfect answers of the targeted question from firestore
        user_answer= request["answers"][count] # to get the user answer of the targeted question from json object
        evaluation_model(user_answer,perfect_answers)
        count+=1
    interview_scores_float= [float(i) for i in interview_scores]
    final_score = sum(interview_scores_float) / len(interview_scores_float)
    print("sum",sum(interview_scores_float),"len",len(interview_scores_float) )
    feedbacks_ids= addFeedbackDocuments(request["questions_ids"],interview_scores_float,evaluate_feedbacks(interview_scores_float))
    # addFeedbackDocuments method add the feedbacks for the targeted interview and give
    # us a return value inclue the auto generated ids of these feedbacks to store feedbacks
    # ids in the interview document in the following line:
    interview_id= setInterview(request["date_time"], feedbacks_ids, request["questions_ids"],request["answers"],final_score)
    addInterviewToUser(request["user_id"],interview_id)
    return {"interview_id":interview_id}

def setInterview(date_time, feedback, questions_ids,answers,final_score):
    #0.069275

    doc_ref = db.collection(INTERVIEW_COLLECTION)
    ref= doc_ref.document()
    ref.set({"date-time":date_time,
                 "feedback":feedback,
                 "interview_questions":questions_ids,
                 "user_answers":answers,
                 "score":final_score})


    print("Done",date_time,feedback,questions_ids,answers,final_score)
    return ref.id

def addInterviewToUser(user_id, interview_id):
    doc_ref= db.collection(USER_COLLECTION).document(user_id)
    doc_ref.update({u'interviews': firestore.ArrayUnion([interview_id])})

def evaluate_feedbacks(interview_feedbacks):
    evaluation=[]
    for interview_feedback in interview_feedbacks:
        if 0.0 < interview_feedback < 0.3:
            evaluation_feed="Your answer is weak, you need to focus on the main core of question"
        elif 0.3 <= interview_feedback < 0.6:
            evaluation_feed="Your answer is good, but if you support it with more detailed personal experiences could be more better"
        elif 0.6 <= interview_feedback < 1.1:
            evaluation_feed="Your answer is really very good and excellent answer"
        else:
            evaluation_feed="Very weak answer"
        evaluation.append(evaluation_feed)
    return evaluation



def getInterviewFeedbacks(interview_feedbacks_ids):
    doc_ref = db.collection(FEEDBACK_COLLECTION)
    feedbacks=[]
    for interview_feedback_id in interview_feedbacks_ids:
         doc= doc_ref.document(str(interview_feedback_id))
         feedbacks.append(doc.get().to_dict())
    return feedbacks


def addFeedbackDocuments(questions_ids, interview_scores,evaluation_feedback):
    doc_ref = db.collection(FEEDBACK_COLLECTION)
    count=0
    feedbacks_ids=[]
    for questions_id in questions_ids:
        ref= doc_ref.document()
        feedbacks_ids.append(ref.id)
        ref.set({"feedback": evaluation_feedback[count],
         "question_id": questions_id,
         "skill_score": interview_scores[count],
                 "skill_name": targeted_skills[count]})
        count+=1
    return feedbacks_ids


def evaluation_model(user_answer, perfect_answers):
        _c = f"""
        {user_answer}
    """
        corpus = [i for i in _c.split('\n') if i != '' and len(i.split(' ')) >= 4]
        corpus_embeddings = model.encode(corpus)
        # typical answer example
        queries = perfect_answers
        query_embeddings = model.encode(queries)
        closest_n = 1
        count = 0  # to calculate the mean (answers scores/sum of answers)
        sum = 0
        for query, query_embedding in zip(queries, query_embeddings):
        # the result of this fr loop is comparing one user answer with all perfect answers
        # of one question
            distances = scipy.spatial.distance.cdist([query_embedding], corpus_embeddings, "cosine")[0]

            results = zip(range(len(distances)), distances)
            results = sorted(results, key=lambda x: x[1])

            # print("\n\n======================\n\n")
            # print("Query:", query)
            # print("\nTop 5 most similar sentences in corpus:")
            for idx, distance in results[0:closest_n]: # we need the closest 1 so for will loop once
                similarity= 1-distance
                sum += similarity
                count += 1
        mean = sum / count
        interview_scores.append("%.4f"%mean)



if __name__ == "__main__":
    app.run(host='0.0.0.0')
