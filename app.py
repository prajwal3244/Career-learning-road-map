from flask import Flask, request, jsonify

app = Flask(__name__)

def generate_roadmap(skills, goal):
    roadmap = "<h3>Your Personalized Roadmap</h3><ul>"

    if int(skills['programming']) < 50:
        roadmap += "<li><strong>1. Learn Programming Fundamentals:</strong><br>"\
                   " -  Choose a language (Python, R).  Python is recommended for beginners.<br>"\
                   " -  Learn basic syntax, data types, and control flow.<br>"\
                   " -  Resources: <a href='https://www.coursera.org/learn/python-for-everybody'>Coursera Python for Everybody</a>, <a href='https://www.learnpython.org/'>LearnPython.org</a></li><br>"
    if int(skills['statistics']) < 50:
        roadmap += "<li><strong>2. Master Statistics and Mathematics:</strong><br>"\
                   " -  Understand descriptive and inferential statistics.<br>"\
                   " -  Learn probability, distributions, and hypothesis testing.<br>"\
                   " -  Brush up on linear algebra and calculus (especially for data science).<br>"\
                   " -  Resources: <a href='https://www.edx.org/course/introduction-statistics-descriptive-inferential'>edX Intro to Stats</a>, <a href='https://www.khanacademy.org/math/statistics-probability'>Khan Academy Statistics and Probability</a></li><br>"
    if int(skills['database']) < 60:
        roadmap += "<li><strong>3. Dive into Databases and SQL:</strong><br>"\
                   " -  Learn database concepts (relational vs. non-relational).<br>"\
                   " -  Master SQL for data querying, manipulation, and management.<br>"\
                   " -  Resources: <a href='https://www.w3schools.com/sql/'>W3Schools SQL Tutorial</a>, <a href='https://www.coursera.org/learn/sql-for-data-science'>Coursera SQL for Data Science</a></li><br>"
    if int(skills['data-viz']) < 70:
        roadmap += "<li><strong>4. Develop Data Visualization Skills:</strong><br>"\
                   " -  Learn to choose the right charts and graphs for different data types.<br>"\
                   " -  Master a visualization tool (Tableau, Power BI, Matplotlib).<br>"\
                   " -  Focus on creating clear, concise, and informative visualizations.<br>"\
                   " -  Resources: <a href='https://www.tableau.com/learn/training'>Tableau Training</a>, <a href='https://powerbi.microsoft.com/en-us/learning/'>Power BI Learning</a></li><br>"

    if goal == "data-scientist":
        roadmap += "<li><strong>5.  Focus on Machine Learning:</strong><br>"\
                    " -  Learn core machine learning algorithms (regression, classification, clustering).<br>"\
                    " -  Understand model selection, training, and evaluation.<br>"\
                    "  - Learn about deep learning.<br>" \
                    " -  Resources: <a href='https://www.coursera.org/specializations/machine-learning'>Coursera Machine Learning</a>, <a href='https://developers.google.com/machine-learning/crash-course'>Google Machine Learning Crash Course</a></li><br>"
    elif goal == "machine-learning-engineer":
        roadmap += "<li><strong>5. Focus on Machine Learning Engineering:</strong><br>"\
                    " -  Learn to deploy and scale machine learning models.<br>"\
                    " -  Understand cloud computing and distributed systems.<br>"\
                    "  - Learn about MLOps practices.<br>" \
                    " -  Resources: <a href='https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops'>Coursera Machine Learning Engineering for Production (MLOps)</a>, <a href='https://cloud.google.com/learn/machine-learning'>Google Cloud ML Learning</a></li><br>"
    elif goal == "data-analyst":
        roadmap += "<li><strong>5. Hone Your Analytical Skills:</strong><br>"\
                   " -  Learn to identify trends, patterns, and insights in data.<br>"\
                   " -  Develop skills in data storytelling and communication.<br>"\
                   " -  Resources: <a href='https://www.coursera.org/professional-certificates/google-data-analytics'>Google Data Analytics Professional Certificate</a>, <a href='https://www.udacity.com/course/data-analyst-nanodegree--nd002'>Udacity Data Analyst Nanodegree</a></li><br>"
    elif goal == "web-developer":
        roadmap += "<li><strong>5. Master Web Development:</strong><br>"\
                   " -  Become proficient in HTML, CSS, and JavaScript.<br>"\
                   " -  Learn a front-end framework (React, Angular, Vue).<br>"\
                   " -  Understand server-side development (Node.js, Python/Django).<br>"\
                   " -  Resources: <a href='https://www.freecodecamp.org/learn/'>freeCodeCamp</a>, <a href='https://developer.mozilla.org/en-US/docs/Web/Learn'>MDN Web Development</a></li><br>"

    roadmap += "<li><strong>6. Build a Portfolio:</strong><br>"\
               " -  Create projects to showcase your skills.<br>"\
               " -  Use platforms like GitHub to host your code.<br>"\
               " -  Contribute to open-source projects.<br>"\
               " -  Resources: <a href='https://www.github.com/'>GitHub</a>, <a href='https://www.kaggle.com/'>Kaggle</a> (for data science projects)</li><br>"
    roadmap += "</ul>"
    return roadmap

def generate_progress():
    progress = "<h3>Weekly Progress</h3><ul>"
    progress += "<li>Week 1: Completed Introduction to Python (25%)</li>"
    progress += "<li>Week 2: Started learning SQL (15%)</li>"
    progress += "<li>Suggestion: Dedicate more time to SQL this week and try to complete the basic concepts.</li>"
    progress += "</ul>"
    return progress

@app.route('/generate_roadmap', methods=['POST'])
def generate_roadmap_route():
    data = request.get_json()
    roadmap = generate_roadmap(data, data['career-goal'])
    progress = generate_progress()
    return jsonify({'roadmap': roadmap, 'progress': progress})

if __name__ == '__main__':
    app.run(debug=True)