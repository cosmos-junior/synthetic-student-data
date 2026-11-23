#EXploratory analysis of the demonstration student data set.

from pathlib import Path
import pandas as pd

#function for analyzing the dataset's statistical characteristics 

def analyze_dataset():
    project_root = Path(__file__).resolve().parents[2]
    file_path = (
        project_root /"data"/ "raw" / "demo_student_data.csv"
    )

    data = pd.read_csv(file_path)
    print("\n=====DATASET OVERVIEW=====")
    print("Shape:", data.shape)
    print("\nData types:")
    print(data.dtypes)

    print("\n=====SUMMARY STATISTICS=====")
    print(data.describe().round(2))

    for column in [
        "gender",
        "programme",
        "grade",
        "academic_status",

    ]:
       print(f"\n{column.upper()}")
       print(data[column].value_counts())

    print("\n=====CORRELATION MATRIX=====")

    numerical_data = data.select_dtypes(include= "number") 

    print(numerical_data.corr().round(3))

    print("\n=====DATA QUALITY=====")
    print("Missing values:")
    print(data.isnull().sum())

    print("\nDuplicate IDs:", data["student_id"].duplicated().sum())

if __name__ =="__main__":
        analyze_dataset()
