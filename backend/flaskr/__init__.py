import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category
from sqlalchemy.testing.config import db

QUESTIONS_PER_PAGE = 10


#Added pagination function for formating questions data into pages
def paginate_questions(request, selection):
  page = request.args.get('page', 1, type=int)
  start =  (page - 1) * QUESTIONS_PER_PAGE
  end = start + QUESTIONS_PER_PAGE

  if page > (len(selection)%QUESTIONS_PER_PAGE):
    abort(404)

  questions = [question.format() for question in selection]
  current_question = questions[start:end]

  return current_question

def create_app(test_config=None):
  # create and configure the app
  app = Flask(__name__)
  setup_db(app)
  
  '''
  Set up CORS. Allow '*' for origins. Delete the sample route after completing the TODOs
  '''
  CORS(app, resource={r"*":{'origins':'*'}})
  '''
  Use the after_request decorator to set Access-Control-Allow
  '''
  @app.after_request
  def after_request(response):
    response.headers.add('Access-Control-Allowed-Headers','Content-Type')
    response.headers.add('Access-Control-Allowed-Methods','GET, POST, DELETE')
    return response

  '''
  Create an endpoint to handle GET requests 
  for all available categories.
  '''
  # Get endpoint for categories
  @app.route('/categories')
  def categories():
     category_list = {}
     categories = Category.query.all()

     if len(categories) == 0:
       abort(404)

     for category in categories:
       category_list[category.id] = category.type

     return jsonify({
       'success' : True,
       'categories': category_list
     })


  '''
  Create an endpoint to handle GET requests for questions, 
  including pagination (every 10 questions). 
  This endpoint should return a list of questions, 
  number of total questions, current category, categories. 

  TEST: At this point, when you start the application
  you should see questions and categories generated,
  ten questions per page and pagination at the bottom of the screen for three pages.
  Clicking on the page numbers should update the questions. 
  '''
  # Get endpoint for questions in pagenated format
  @app.route('/questions')
  def questions():
    category_list = {}
    categories = Category.query.all()

    if len(categories) == 0:
      abort(404)

    for category in categories:
      category_list[category.id] = category.type


    questions = Question.query.all()

    if len(questions) == 0:
      abort(404)

    current_question = paginate_questions(request, questions)

    return jsonify({
       'success' : True,
       'questions' : current_question,
       'Total_questions' : len(questions),
       'categories' : category_list 
     })

  '''
  Create an endpoint to DELETE question using a question ID. 

  TEST: When you click the trash icon next to a question, the question will be removed.
  This removal will persist in the database and when you refresh the page. 
  '''
  @app.route('/questions/<int:question_id>', methods=['DELETE'])
  def delete_question(question_id):
    question = Question.query.filter(Question.id == question_id)\
      .one_or_none()

    if question is None:
      abort(404)

    try:
      question.delete()
    except :
      db.session.rollback()
      abort(422)
    finally:
      questions = Question.query.all()
      current_questions = paginate_questions(request, questions)

    return jsonify({
      'success' : True,
      'questions' : current_questions,
      'Total_questions' : len(questions),
      'deleted' : question_id
    })

  '''
  Create an endpoint to POST a new question, 
  which will require the question and answer text, 
  category, and difficulty score.

  Create a POST endpoint to get questions based on a search term. 
  It should return any questions for whom the search term 
  is a substring of the question. 

  TEST: When you submit a question on the "Add" tab, 
  the form will clear and the question will appear at the end of the last page
  of the questions list in the "List" tab.  
  '''

  @app.route('/questions', methods=['POST'])
  def add_questions():
    # load the request body
    body = request.get_json()

    # if search term is present
    if (body.get('searchTerm')):
      search_term = body.get('searchTerm')

      questions = Question.query\
        .filter(Question.question.ilike(f'%{search_term}%')).all()

      if (len(questions) == 0):
          abort(404)
          
      current_questions = paginate_questions(request, questions)

      # return results
      return jsonify({
        'success': True,
        'questions': current_questions,
        'total_questions': len(current_questions)
      })
        
    # if no search term, create new question
    else:
      new_question = body.get('question')
      new_answer = body.get('answer')
      new_difficulty = body.get('difficulty')
      new_category = body.get('category')

      # check if all fields have data
      if ((new_question is None) or (new_answer is None)
            or (new_difficulty is None) or (new_category is None)):
            abort(400)

      question = Question(question=new_question,answer=new_answer,
                    category=new_category,difficulty=new_difficulty)

      try:
        question.insert()
      except:
        db.session.rollback()
        abort(422)
      finally:
        questions = Question.query.all()
        current_questions = paginate_questions(request, questions)

      if len(current_questions) == 0:
        abort(404)

      return jsonify({
        'success' : True,
        'questions' : current_questions,
        'Total_questions' : len(questions)
      })

  ''' 
  Create a GET endpoint to get questions based on category. 

  TEST: In the "List" tab / main screen, clicking on one of the 
  categories in the left column will cause only questions of that 
  category to be shown. 
  '''
  @app.route('/categories/<int:category_id>/questions')
  def question_by_category(category_id):
    
    categories = Category.query.filter_by(id = category_id).one_or_none()

    if categories is None:
      abort(404)

    questions = Question.query.filter(Question.category == category_id).all()

    if len(questions) == 0:
      abort(404)

    current_question = paginate_questions(request, questions)

    return jsonify({
       'success' : True,
       'questions' : current_question,
       'Total_questions' : len(questions) 
     })



  '''
  Create a POST endpoint to get questions to play the quiz. 
  This endpoint should take category and previous question parameters 
  and return a random questions within the given category, 
  if provided, and that is not one of the previous questions. 

  TEST: In the "Play" tab, after a user selects "All" or a category,
  one question at a time is displayed, the user is allowed to answer
  and shown whether they were correct or not. 
  '''
  @app.route('/quizzes', methods=['POST'])
  def play_quiz():
    # load the request body
    body = request.get_json()

    #get quiz category and previous questions list
    quiz_category = body.get('quiz_category')

    prev_question = body.get('previous_questions')

    if quiz_category is None:
      abort(422)

    if quiz_category['id'] == 0:
      questions = Question.query\
          .filter(Question.id.notin_(prev_question)).all()
    else:
      questions = Question.query.filter_by(category=quiz_category['id'])\
          .filter(Question.id.notin_(prev_question)).all()

    if len(questions) == 0:
      return jsonify({
        'success' : True,
        'question' : None
      })

    new_question = random.choices(questions, k=1)
    
    next_question = Question.query.filter_by(id = new_question[0].id)\
      .one_or_none()

    if questions is None:
      abort(404)

    return jsonify({
       'success' : True,
       'question' : next_question.format()
     })

  '''
  Create error handlers for all expected errors 
  including 404 and 422. 
  '''
  @app.errorhandler(404)
  def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": "resource not found"
      }), 404

  @app.errorhandler(422)
  def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": "unprocessable"
      }), 422

  @app.errorhandler(400)
  def bad_request(error):
    return jsonify({
        "success": False,
        "error": 400,
        "message": "bad request"
      }), 400

  return app

    