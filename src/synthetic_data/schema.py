"""student data schema , defines fields, categories and domain constraintsfor the project database """

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

ID_COLUMN =[
    "student_id"
]
PROGRAMMES=["BIT", "BCS", "BSE", "BACMP", "BBIT"]
GENDERS=["Male","Female"]
GRADES=["A", "B", "C", "D", "E" ]
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

