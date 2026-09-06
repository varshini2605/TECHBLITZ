import os
from datetime import datetime
from flask import current_app
from models import db, Admin, Test, Question, Registration

SAMPLE_QUESTIONS = [
    {
        'topic': 'Programming',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'In Python, what is the output of `type(lambda: None)`?',
        'option_a': "<class 'function'>",
        'option_b': "<class 'lambda'>",
        'option_c': "<class 'object'>",
        'option_d': "<class 'generator'>",
        'correct_answer': 'A',
        'explanation': 'Lambdas in Python create first-class anonymous function objects, whose type is function.'
    },
    {
        'topic': 'Data Structures',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'Which data structure follows the Last-In-First-Out (LIFO) order of elements?',
        'option_a': 'Queue',
        'option_b': 'Stack',
        'option_c': 'Linked List',
        'option_d': 'Binary Tree',
        'correct_answer': 'B',
        'explanation': 'A Stack operates strictly on LIFO (Last-In-First-Out).'
    },
    {
        'topic': 'Data Structures',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'What is the worst-case lookup time complexity in a Hash Table when many collisions occur and are resolved using chaining?',
        'option_a': 'O(1)',
        'option_b': 'O(log n)',
        'option_c': 'O(n)',
        'option_d': 'O(n log n)',
        'correct_answer': 'C',
        'explanation': 'If all keys hash to the same bucket, lookup degenerates to searching a linked list of length n, which is O(n).'
    },
    {
        'topic': 'Algorithms',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'What is the tight asymptotic upper bound of Merge Sort for an array of size n?',
        'option_a': 'O(n)',
        'option_b': 'O(n log n)',
        'option_c': 'O(n^2)',
        'option_d': 'O(2^n)',
        'correct_answer': 'B',
        'explanation': 'Merge Sort recursively divides the array into halves and merges in linear time, guaranteeing O(n log n) in all cases.'
    },
    {
        'topic': 'Algorithms',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'Which algorithmic design strategy is used by Kruskal’s Minimum Spanning Tree algorithm?',
        'option_a': 'Dynamic Programming',
        'option_b': 'Greedy Method',
        'option_c': 'Divide and Conquer',
        'option_d': 'Backtracking',
        'correct_answer': 'B',
        'explanation': 'Kruskal’s algorithm sorts edges by weight and greedily selects the minimum weight edge that does not form a cycle.'
    },
    {
        'topic': 'DBMS',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'Which property of ACID ensures that a database transaction is either fully completed or completely rolled back?',
        'option_a': 'Atomicity',
        'option_b': 'Consistency',
        'option_c': 'Isolation',
        'option_d': 'Durability',
        'correct_answer': 'A',
        'explanation': 'Atomicity represents the all-or-nothing guarantee of transaction processing.'
    },
    {
        'topic': 'DBMS',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'Which normal form is designed to eliminate transitive dependencies in relational database schemas?',
        'option_a': 'First Normal Form (1NF)',
        'option_b': 'Second Normal Form (2NF)',
        'option_c': 'Third Normal Form (3NF)',
        'option_d': 'Boyce-Codd Normal Form (BCNF)',
        'correct_answer': 'C',
        'explanation': '3NF requires that a relation is in 2NF and that no non-prime attribute is transitively dependent on any candidate key.'
    },
    {
        'topic': 'Operating Systems',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'Which of the following conditions is NOT one of the four Coffman conditions required for a deadlock?',
        'option_a': 'Mutual Exclusion',
        'option_b': 'Hold and Wait',
        'option_c': 'Preemption Allowed',
        'option_d': 'Circular Wait',
        'correct_answer': 'C',
        'explanation': 'Deadlock requires NO PREEMPTION. If preemption is allowed, deadlock cannot persist.'
    },
    {
        'topic': 'Operating Systems',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'What is the main purpose of the Translation Lookaside Buffer (TLB) in virtual memory systems?',
        'option_a': 'To cache hard drive page writes',
        'option_b': 'To cache virtual-to-physical address translations',
        'option_c': 'To prevent stack overflow errors',
        'option_d': 'To synchronize CPU registers across cores',
        'correct_answer': 'B',
        'explanation': 'The TLB is a high-speed associative hardware cache that speeds up virtual-to-physical address translation.'
    },
    {
        'topic': 'Computer Networks',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'Which transport-layer protocol is connection-oriented, guarantees in-order packet delivery, and implements flow control?',
        'option_a': 'UDP',
        'option_b': 'TCP',
        'option_c': 'ICMP',
        'option_d': 'IP',
        'correct_answer': 'B',
        'explanation': 'TCP (Transmission Control Protocol) is connection-oriented and guarantees reliable, sequenced delivery.'
    },
    {
        'topic': 'Computer Networks',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'What is the default subnet mask for a standard Class C IPv4 address network?',
        'option_a': '255.0.0.0',
        'option_b': '255.255.0.0',
        'option_c': '255.255.255.0',
        'option_d': '255.255.255.255',
        'correct_answer': 'C',
        'explanation': 'Class C networks allocate 24 bits for the network identifier, giving 255.255.255.0 (/24).'
    },
    {
        'topic': 'Computer Architecture',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'In computer architecture pipelining, what hazard occurs when an instruction depends on the result of a previous instruction that is still in flight?',
        'option_a': 'Structural Hazard',
        'option_b': 'Data Hazard (RAW)',
        'option_c': 'Control Hazard',
        'option_d': 'Branch Misprediction Hazard',
        'correct_answer': 'B',
        'explanation': 'A Data Hazard occurs when instructions that exhibit data dependence modify or access data in different pipeline stages.'
    },
    {
        'topic': 'Aptitude',
        'difficulty': 'Medium',
        'marks': 2.0,
        'question_text': 'A train traveling at 72 km/h crosses a pole in 15 seconds. What is the length of the train?',
        'option_a': '200 meters',
        'option_b': '250 meters',
        'option_c': '300 meters',
        'option_d': '350 meters',
        'correct_answer': 'C',
        'explanation': 'Speed in m/s = 72 * (5/18) = 20 m/s. Distance (length) = Speed * Time = 20 * 15 = 300 meters.'
    },
    {
        'topic': 'Logical Reasoning',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'Find the next number in the sequence: 2, 6, 12, 20, 30, ?',
        'option_a': '40',
        'option_b': '42',
        'option_c': '44',
        'option_d': '46',
        'correct_answer': 'B',
        'explanation': 'Differences are +4, +6, +8, +10, so next difference is +12. 30 + 12 = 42.'
    },
    {
        'topic': 'General Technical Knowledge',
        'difficulty': 'Easy',
        'marks': 1.0,
        'question_text': 'Which git command creates a new branch and immediately checks it out in a single step?',
        'option_a': 'git branch -c <name>',
        'option_b': 'git checkout -b <name>',
        'option_c': 'git commit -b <name>',
        'option_d': 'git switch --force <name>',
        'correct_answer': 'B',
        'explanation': '`git checkout -b <name>` (or `git switch -c <name>`) creates and checks out the new branch.'
    }
]

SAMPLE_REGISTRATIONS = [
    {'ht': 'TB001', 'name': 'Rahul', 'team': 'TEAM01', 'email': 'rahul@college.edu'},
    {'ht': 'TB002', 'name': 'Priya', 'team': 'TEAM01', 'email': 'priya@college.edu'},
    {'ht': 'TB003', 'name': 'Arjun', 'team': 'TEAM02', 'email': 'arjun@college.edu'},
    {'ht': 'TB004', 'name': 'Kiran', 'team': 'TEAM02', 'email': 'kiran@college.edu'}
]

def seed_database():
    """
    Initializes database tables, creates default admin, default test, sample questions, and sample registrations.
    """
    db.create_all()

    # 1. Admin account
    admin_username = current_app.config.get('ADMIN_USERNAME')
    admin_password = current_app.config.get('ADMIN_PASSWORD')
    if not admin_username or not admin_password:
        raise RuntimeError('ADMIN_USERNAME and ADMIN_PASSWORD must be configured before seeding the database.')

    admin = Admin.query.filter_by(username=admin_username).first()
    if not admin:
        admin = Admin(username=admin_username)
        admin.set_password(admin_password)
        db.session.add(admin)
        print(f"[Seed] Created Admin user: {admin_username}")

    # 2. Default Test: TECHBLITZ ROUND 1
    test = Test.query.filter_by(test_id='TB2026').first()
    if not test:
        test = Test(
            test_id='TB2026',
            name='TECHBLITZ ROUND 1',
            description='Smart Browser-Monitored Online Assessment for College Coding Club',
            duration_minutes=20,
            randomize_questions=False,
            randomize_options=False,
            max_violations=3,
            auto_block=True,
            auto_terminate=False,
            active=True
        )
        db.session.add(test)
        db.session.flush()
        print("[Seed] Created default test: TECHBLITZ ROUND 1 (TB2026)")
    else:
        test.duration_minutes = 20
        db.session.commit()

    # 3. Questions
    if Question.query.filter_by(test_id=test.id).count() == 0:
        for idx, item in enumerate(SAMPLE_QUESTIONS, start=1):
            q = Question(
                test_id=test.id,
                question_text=item['question_text'],
                option_a=item['option_a'],
                option_b=item['option_b'],
                option_c=item['option_c'],
                option_d=item['option_d'],
                correct_answer=item['correct_answer'],
                marks=item['marks'],
                topic=item['topic'],
                difficulty=item['difficulty'],
                explanation=item['explanation'],
                order_index=idx
            )
            db.session.add(q)
        test.recalculate_total_marks()
        print(f"[Seed] Added {len(SAMPLE_QUESTIONS)} sample technical MCQs to test {test.test_id}")

    # 4. Sample Registrations
    for item in SAMPLE_REGISTRATIONS:
        norm_ht = Registration.normalize_string(item['ht'])
        existing = Registration.query.filter_by(normalized_hall_ticket=norm_ht).first()
        if not existing:
            reg = Registration(
                hall_ticket_number=item['ht'],
                normalized_hall_ticket=norm_ht,
                name=item['name'],
                team_id=item['team'],
                normalized_team_id=Registration.normalize_string(item['team']),
                email=item['email'],
                status='ACTIVE',
                source_file='Demo Registration'
            )
            db.session.add(reg)
            print(f"[Seed] Added demo registration: {item['ht']} - {item['name']} ({item['team']})")

    db.session.commit()
    print("[Seed] Database successfully initialized and seeded.")

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_database()
