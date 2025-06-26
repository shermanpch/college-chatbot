"""
Test questions for RAGAS evaluation of the retrieval system.

This module contains the standardized set of test questions used to evaluate
the performance of the self-query retriever across various query types and
complexity levels. Each question includes expected target universities for
accuracy evaluation.
"""

from dataclasses import dataclass


@dataclass
class TestQuestion:
    """
    Represents a single test question with all associated metadata.

    Attributes:
        question_id: Unique identifier for the question
        question: The actual question text
        expected_targets: List of expected university names that should be retrieved
        attributes_used: List of attributes/filters used in the query
    """

    question_id: str
    question: str
    expected_targets: list[str]
    attributes_used: list[str]


class TestQuestionCollection:
    """
    Collection of test questions with methods for accessing and filtering.
    """

    def __init__(self):
        """Initialize the collection with predefined test questions."""
        self._questions = self._initialize_questions()

    def _initialize_questions(self) -> list[TestQuestion]:
        """Initialize all test questions."""
        return [
            TestQuestion(
                question_id="Q001",
                question="Which universities in Massachusetts have an acceptance rate of 25% or lower, and a 75th percentile SAT Math score of 750 or higher?",
                expected_targets=["Smith College"],
                attributes_used=[
                    "state == 'Massachusetts'",
                    "accept_rate <= 0.25",
                    "sat_math_75 >= 750",
                ],
            ),
            TestQuestion(
                question_id="Q002",
                question="Find universities in Pennsylvania with a student-faculty ratio of 13:1 or better, where the application fee is not reported (or is $0), and that offer Bachelor's degrees in Computer Science.",
                expected_targets=[
                    "Duquesne University",
                    "Immaculata University",
                    "Waynesburg University",
                    "Gannon University",
                ],
                attributes_used=[
                    "state == 'Pennsylvania'",
                    "student_faculty_ratio <= 13.0",
                    "(application_fee == null OR application_fee == 0)",
                ],
            ),
            TestQuestion(
                question_id="Q003",
                question="Which universities in California offer college-owned housing and have an average financial aid package greater than $60,000?",
                expected_targets=["California Institute of Technology"],
                attributes_used=[
                    "state == 'California'",
                    "college_owned_housing == true",
                    "avg_financial_aid_package > 60000",
                ],
            ),
            TestQuestion(
                question_id="Q004",
                question="List universities with an out-of-state tuition under $20,000, an acceptance rate above 80 percent, and which offer football as a sport.",
                expected_targets=["West Virginia State University"],
                attributes_used=[
                    "tuition_out_of_state < 20000",
                    "accept_rate > 0.80",
                    "sport_football == true",
                ],
            ),
            TestQuestion(
                question_id="Q005",
                question="Which universities have a 25th percentile ACT Composite score of 30 or higher, and an average high school GPA of 3.7 or higher (or GPA is not reported)?",
                expected_targets=[
                    "Franklin & Marshall College",
                    "Georgetown University",
                    "University of Notre Dame",
                    "Wesleyan University",
                    "Smith College",
                    "Skidmore College",
                    "Boston University",
                ],
                attributes_used=[
                    "act_composite_25 >= 30",
                    "(avg_high_school_gpa >= 3.7 OR avg_high_school_gpa == null)",
                ],
            ),
            TestQuestion(
                question_id="Q006",
                question="Find universities in New York that offer a Bachelor's degree in Biology, have a student-faculty ratio of 12:1 or less, and where room and board costs less than $18,000.",
                expected_targets=[
                    "Keuka College",
                    "Albany College of Pharmacy and Health Sciences",
                    "Roberts Wesleyan University",
                ],
                attributes_used=[
                    "state == 'New York'",
                    "student_faculty_ratio <= 12.0",
                    "room_and_board < 18000",
                ],
            ),
            TestQuestion(
                question_id="Q007",
                question="Which universities with reported private tuition have a total faculty count greater than 500, offer women's basketball, and where at least 95% of students in need receive financial aid?",
                expected_targets=[
                    "Duquesne University",
                    "Aurora University",
                    "Fairfield University",
                    "Boston University",
                    "Georgetown University",
                    "University of Notre Dame",
                    "Mercer University",
                    "Monmouth University",
                    "Endicott College",
                ],
                attributes_used=[
                    "tuition_private > 0",
                    "total_faculty > 500",
                    "sport_basketball == true",
                    "percentage_need_receive_financial_aid >= 0.95",
                ],
            ),
            TestQuestion(
                question_id="Q008",
                question="List universities where housing is required for the first year, the percentage of students living on campus is over 75% (i.e., > 0.75), and they offer men's soccer.",
                expected_targets=[
                    "Skidmore College",
                    "California Institute of Technology",
                    "Albion College",
                    "Bucknell University",
                    "University of Notre Dame",
                    "Wesleyan University",
                ],
                attributes_used=[
                    "housing_required_first_year == true",
                    "percent_students_on_campus > 0.75",
                    "sport_soccer == true",
                ],
            ),
            TestQuestion(
                question_id="Q009",
                question="Which universities in Illinois have an application fee of $50 or more and an average grant aid of at least $6,000?",
                expected_targets=["University of Illinois Chicago"],
                attributes_used=[
                    "state == 'Illinois'",
                    "application_fee >= 50",
                    "avg_grant_aid >= 6000",
                ],
            ),
            TestQuestion(
                question_id="Q010",
                question="Find universities that offer athletic scholarships for any sport, have a 75th percentile SAT Verbal (Critical Reading) score of 650 or higher, and are NOT located in Boston or New York City.",
                expected_targets=[
                    "Duquesne University",
                    "University of Evansville",
                    "Fairfield University",
                    "Bucknell University",
                    "University of Colorado Boulder",
                    "Mercer University",
                    "University of Notre Dame",
                    "Georgetown University",
                ],
                attributes_used=[
                    "scholarship_sports_available == true",
                    "sat_verbal_75 >= 650",
                    "city != 'Boston'",
                    "city != 'New York City'",
                ],
            ),
            TestQuestion(
                question_id="Q011",
                question="Which universities have a student body with more than 60% women (female percentage > 0.60) and an acceptance rate between 50% and 80% (inclusive)?",
                expected_targets=[
                    "University of Montevallo",
                    "Keuka College",
                    "University of Charleston",
                    "Rosemont College",
                    "Tusculum University",
                    "Fresno Pacific University",
                    "Northpoint Bible College",
                ],
                attributes_used=[
                    "percent_women > 0.60",
                    "accept_rate >= 0.50",
                    "accept_rate <= 0.80",
                ],
            ),
            TestQuestion(
                question_id="Q012",
                question="List universities in Florida or Georgia that have an average financial aid package below $25,000 and offer a Bachelor's degree in Business Administration.",
                expected_targets=[
                    "University of West Florida",
                    "Ave Maria University",
                    "ECPI University-Worldwide",
                    "Lynn University",
                    "Emmanuel University",
                ],
                attributes_used=[
                    "(state == 'Florida' OR state == 'Georgia')",
                    "avg_financial_aid_package < 25000",
                ],
            ),
            TestQuestion(
                question_id="Q013",
                question="Which universities do not report an average high school GPA, have a 25th percentile ACT composite score of 20 or less (or score is not reported), and offer men's baseball?",
                expected_targets=[
                    "The University of Texas at San Antonio",
                    "Crowley's Ridge College",
                ],
                attributes_used=[
                    "avg_high_school_gpa == null",
                    "(act_composite_25 <= 20 OR act_composite_25 == null)",
                    "sport_baseball == true",
                ],
            ),
            TestQuestion(
                question_id="Q014",
                question="Find universities with a total faculty count between 100 and 300, an application fee of exactly $50, and that offer lacrosse.",
                expected_targets=["Oglethorpe University"],
                attributes_used=[
                    "total_faculty >= 100",
                    "total_faculty <= 300",
                    "application_fee == 50",
                    "sport_lacrosse == true",
                ],
            ),
            TestQuestion(
                question_id="Q015",
                question="Which universities in Ohio have an in-state tuition greater than $6,000 but less than $10,000, and offer a Bachelor's degree in Psychology?",
                expected_targets=["Ohio University-Chillicothe"],
                attributes_used=[
                    "state == 'Ohio'",
                    "tuition_in_state > 6000",
                    "tuition_in_state < 10000",
                ],
            ),
            TestQuestion(
                question_id="Q016",
                question="List universities that offer both men's golf and women's golf, and have a student-faculty ratio of 15:1 or higher.",
                expected_targets=[
                    "The University of Texas at San Antonio",
                    "Central State University",
                    "Aurora University",
                    "Texas A&M University",
                    "Southern Utah University",
                    "University of Missouri",
                    "University of Toledo",
                    "University of Washington",
                    "Fayetteville State University",
                    "University of Central Missouri",
                    "Mississippi State University",
                    "University of Central Arkansas",
                    "Lindsey Wilson College",
                ],
                attributes_used=["sport_golf == true", "student_faculty_ratio >= 15.0"],
            ),
            TestQuestion(
                question_id="Q017",
                question="Which universities have a 75th percentile SAT Math score of 780 or higher AND a 75th percentile SAT Critical Reading (Verbal) score of 760 or higher?",
                expected_targets=[
                    "Smith College",
                    "University of Notre Dame",
                    "Georgetown University",
                ],
                attributes_used=["sat_math_75 >= 780", "sat_verbal_75 >= 760"],
            ),
            TestQuestion(
                question_id="Q018",
                question="Find universities where 100% of students in need receive financial aid, and the average grant aid is over $30,000.",
                expected_targets=[
                    "Georgetown University",
                    "University of Notre Dame",
                    "Wesleyan University",
                    "Illinois Wesleyan University",
                    "Cornell College",
                    "Boston University",
                ],
                attributes_used=[
                    "percentage_need_receive_financial_aid == 1.0",
                    "avg_grant_aid > 30000",
                ],
            ),
            TestQuestion(
                question_id="Q019",
                question="Which universities are located in 'Chicago, Illinois' or 'Philadelphia, Pennsylvania', and have an acceptance rate below 85 percent?",
                expected_targets=[
                    "Illinois Institute of Technology",
                    "Rush University",
                    "Curtis Institute of Music",
                    "Holy Family University",
                    "Northeastern Illinois University",
                ],
                attributes_used=[
                    "((city == 'Chicago' AND state == 'Illinois') OR (city == 'Philadelphia' AND state == 'Pennsylvania'))",
                    "accept_rate < 0.85",
                ],
            ),
            TestQuestion(
                question_id="Q020",
                question="List universities that offer a Bachelor's degree in 'Accounting', have an application fee greater than $40 (or fee is not reported), and offer college-owned housing.",
                expected_targets=[
                    "Babson College",
                    "The University of Texas at San Antonio",
                    "Texas A&M University",
                    "University of Delaware",
                    "Fairfield University",
                    "Bucknell University",
                    "University of Colorado Boulder",
                    "Boston University",
                    "Georgetown University",
                    "University of Notre Dame",
                    "University of Washington",
                    "Mercer University",
                    "Monmouth University",
                    "Oglethorpe University",
                    "Lynn University",
                    "Endicott College",
                    "Holy Cross College",
                    "Duquesne University",
                    "University of Evansville",
                    "Illinois Wesleyan University",
                    "Roberts Wesleyan University",
                    "Quincy University",
                    "Grove City College",
                    "Dakota Wesleyan University",
                    "Central Christian College of Kansas",
                    "Clarke University",
                    "Midland University",
                    "George Fox University",
                    "Franciscan University of Steubenville",
                    "D'Youville University",
                    "Indiana University South Bend",
                    "Saint Joseph's College of Maine",
                ],
                attributes_used=[
                    "(application_fee > 40 OR application_fee == null)",
                    "college_owned_housing == true",
                ],
            ),
        ]

    def get_question_by_index(self, index: int) -> TestQuestion | None:
        """Get a question by its 1-based index."""
        if 1 <= index <= len(self._questions):
            return self._questions[index - 1]
        return None

    def __len__(self) -> int:
        """Return number of questions."""
        return len(self._questions)


# Create the global instance
test_questions = TestQuestionCollection()
