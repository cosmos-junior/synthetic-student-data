"""student data schema , defines fields, categories and domain constraintsfor the project database """

REG_COLUMN =[
    "student_reg"
]


NUMERIC_COLUMNS =[
    "age",
    "year of study",
    "attendance_percentage",
    "coursework_score",
    "exam_score",
    "final_score"
]

CATEGORICAL_COLUMNS =[
    "gender",
    "programme",
    "grade",
    "academic_status",
]

REQUIRED_COLUMNS = [
    REG_COLUMN,
    *NUMERIC_COLUMNS,
    *CATEGORICAL_COLUMNS,
]


PROGRAMMES=["BIT", "BCS", "BSE", "BACMP", "BBIT"]
GENDERS=["Male","Female"]
GRADES=["A", "B", "C", "D", "F" ]
ACADEMIC_STATUS=["Pass", "Fail"]
COLUMN_RANGES = {
    "age": (17, 35),
    "year_of_study": (1, 4),
    "attendance_percentage": (0, 100),
    "coursework_score": (0, 100),
    "exam_score": (0, 100),
    "final_score": (0, 100),
}
PASS_MARK = 40
COURSEWORK_WEIGHT= 0.40
EXAM_WEIGHT = 0.60

def determine_grade(score):
    #return the project defined grade for a final score
    if score >= 70 :
        return "A"
    if score >= 60:
        return "B"
    if score >=50:
        return "C"
    if score >= 40:
        return "D"
    return "F"

def determone_status(score):
    #determine whether a student passes or fails.determone_status
    return "Pass" if score >= PASS_MARK else "Fail"