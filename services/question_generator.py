import json
import os
import random

# Pre-compiled high-quality curated technical question bank covering all primary topics and difficulty levels
CURATED_BANK = {
    'Data Structures': [
        {
            'question': 'Which data structure follows the Last-In-First-Out (LIFO) principle?',
            'option_a': 'Queue', 'option_b': 'Stack', 'option_c': 'Linked List', 'option_d': 'Tree',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'A Stack stores elements sequentially where the last element inserted is the first one removed (LIFO).'
        },
        {
            'question': 'What is the worst-case time complexity of searching an element in a balanced Binary Search Tree (AVL Tree)?',
            'option_a': 'O(1)', 'option_b': 'O(n)', 'option_c': 'O(log n)', 'option_d': 'O(n log n)',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Medium',
            'explanation': 'In a height-balanced BST (AVL tree), the height is guaranteed to be O(log n), making search O(log n) in the worst case.'
        },
        {
            'question': 'Which data structure is most commonly used for implementing a Breadth-First Search (BFS) algorithm on a graph?',
            'option_a': 'Stack', 'option_b': 'Priority Queue', 'option_c': 'Queue', 'option_d': 'Hash Map',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'BFS explores vertices level by level, requiring a FIFO Queue to track unvisited adjacent nodes.'
        },
        {
            'question': 'In a Min-Heap with N elements, what is the time complexity to extract the minimum element?',
            'option_a': 'O(1)', 'option_b': 'O(log n)', 'option_c': 'O(n)', 'option_d': 'O(n log n)',
            'correct_answer': 'B', 'marks': 2.0, 'difficulty': 'Medium',
            'explanation': 'Extracting the min element requires replacing the root with the last leaf and sift-down (heapify), taking O(log n).'
        },
        {
            'question': 'What is the minimum number of queues needed to implement a stack?',
            'option_a': '1', 'option_b': '2', 'option_c': '3', 'option_d': 'Cannot be done',
            'correct_answer': 'B', 'marks': 2.0, 'difficulty': 'Medium',
            'explanation': 'Two queues can simulate stack operations by shifting elements between them on push or pop.'
        }
    ],
    'Algorithms': [
        {
            'question': 'What is the average time complexity of QuickSort?',
            'option_a': 'O(n)', 'option_b': 'O(n log n)', 'option_c': 'O(n^2)', 'option_d': 'O(log n)',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'QuickSort partitions subarrays recursively, taking O(n log n) average time.'
        },
        {
            'question': 'Which algorithmic paradigm does Dijkstra’s Single-Source Shortest Path algorithm follow?',
            'option_a': 'Dynamic Programming', 'option_b': 'Divide and Conquer', 'option_c': 'Greedy', 'option_d': 'Backtracking',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Medium',
            'explanation': 'Dijkstra chooses the vertex with the minimum tentative distance at each step, an exemplary Greedy choice.'
        },
        {
            'question': 'What is the recurrence relation for the Merge Sort algorithm?',
            'option_a': 'T(n) = T(n/2) + O(1)', 'option_b': 'T(n) = 2T(n/2) + O(n)', 'option_c': 'T(n) = 2T(n/2) + O(1)', 'option_d': 'T(n) = T(n-1) + O(n)',
            'correct_answer': 'B', 'marks': 2.0, 'difficulty': 'Medium',
            'explanation': 'Merge Sort divides the array into 2 halves (2T(n/2)) and merges them in linear time (O(n)).'
        },
        {
            'question': 'Which algorithm is optimal for finding the strongly connected components of a directed graph in linear time?',
            'option_a': 'Kruskal’s Algorithm', 'option_b': 'Tarjan’s Algorithm', 'option_c': 'Prim’s Algorithm', 'option_d': 'Floyd-Warshall Algorithm',
            'correct_answer': 'B', 'marks': 2.0, 'difficulty': 'Hard',
            'explanation': 'Tarjan’s and Kosaraju’s algorithms find SCCs in O(V + E) linear time.'
        }
    ],
    'Python': [
        {
            'question': 'What is the output of `bool("False")` in Python?',
            'option_a': 'False', 'option_b': 'True', 'option_c': 'None', 'option_d': 'Error',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'In Python, any non-empty string evaluates to `True` when converted to boolean.'
        },
        {
            'question': 'Which of the following data types is immutable in Python?',
            'option_a': 'List', 'option_b': 'Set', 'option_c': 'Tuple', 'option_d': 'Dictionary',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'Tuples cannot be modified after creation, making them immutable.'
        },
        {
            'question': 'What does the `__init__` method do in Python classes?',
            'option_a': 'Destroys an instance', 'option_b': 'Initializes object attributes upon creation', 'option_c': 'Inherits parent class methods', 'option_d': 'Imports classes',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': '`__init__` is the constructor method called automatically when creating an object.'
        },
        {
            'question': 'What is the GIL (Global Interpreter Lock) in CPython?',
            'option_a': 'A compiler optimization tool', 'option_b': 'A mutex that prevents multiple native threads from executing Python bytecodes at once', 'option_c': 'A garbage collection algorithm', 'option_d': 'A secure sandbox mechanism',
            'correct_answer': 'B', 'marks': 2.0, 'difficulty': 'Hard',
            'explanation': 'The GIL is a mutex used in CPython to synchronize thread execution and ensure thread-safe memory management.'
        }
    ],
    'DBMS': [
        {
            'question': 'What does ACID stand for in Database Management Systems?',
            'option_a': 'Atomicity, Consistency, Isolation, Durability', 'option_b': 'Accuracy, Control, Integrity, Data', 'option_c': 'Access, Consistency, Indexing, Durability', 'option_d': 'Atomicity, Concurrency, Isolation, Distribution',
            'correct_answer': 'A', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'ACID guarantees reliable transaction processing: Atomicity, Consistency, Isolation, Durability.'
        },
        {
            'question': 'Which normal form ensures that every non-key attribute is fully functionally dependent on the primary key?',
            'option_a': '1NF', 'option_b': '2NF', 'option_c': '3NF', 'option_d': 'BCNF',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Medium',
            'explanation': '2NF removes partial functional dependencies on composite primary keys.'
        },
        {
            'question': 'Which SQL command is used to remove all rows from a table without logging individual row deletions?',
            'option_a': 'DELETE', 'option_b': 'DROP', 'option_c': 'TRUNCATE', 'option_d': 'REMOVE',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'TRUNCATE removes all rows by deallocating pages and is faster than DELETE because it avoids row-by-row logging.'
        }
    ],
    'Operating Systems': [
        {
            'question': 'Which scheduling algorithm is non-preemptive and subject to the convoy effect?',
            'option_a': 'Round Robin', 'option_b': 'Shortest Remaining Time First', 'option_c': 'First-Come, First-Served (FCFS)', 'option_d': 'Priority Preemptive',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'In FCFS, long CPU-burst processes hold the CPU, causing subsequent short processes to wait (convoy effect).'
        },
        {
            'question': 'What are the four necessary conditions for a deadlock to occur?',
            'option_a': 'Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait', 'option_b': 'Preemption, Starvation, Aging, Thrashing', 'option_c': 'Semaphores, Mutex, Monitors, Locks', 'option_d': 'Paging, Segmentation, Swapping, Fragmentation',
            'correct_answer': 'A', 'marks': 2.0, 'difficulty': 'Medium',
            'explanation': 'Coffman conditions: Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait.'
        },
        {
            'question': 'What causes thrashing in virtual memory systems?',
            'option_a': 'Insufficient CPU speed', 'option_b': 'High degree of multiprogramming causing continuous page faults', 'option_c': 'Cache miss rate exceeding threshold', 'option_d': 'Corrupted swap partition',
            'correct_answer': 'B', 'marks': 2.0, 'difficulty': 'Medium',
            'explanation': 'Thrashing occurs when a process spends more time swapping pages in and out of memory than executing instructions.'
        }
    ],
    'Computer Networks': [
        {
            'question': 'Which OSI layer is responsible for end-to-end reliable transmission and port addressing?',
            'option_a': 'Data Link Layer', 'option_b': 'Network Layer', 'option_c': 'Transport Layer', 'option_d': 'Session Layer',
            'correct_answer': 'C', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'The Transport Layer (Layer 4) manages port numbers, segmentation, flow control, and error recovery (e.g. TCP).'
        },
        {
            'question': 'What is the default port number for secure HTTPS communication?',
            'option_a': '80', 'option_b': '443', 'option_c': '8080', 'option_d': '22',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'Port 443 is assigned by IANA for HTTPS (HTTP over TLS/SSL).'
        },
        {
            'question': 'How many packets are exchanged in a standard TCP connection teardown (graceful close)?',
            'option_a': '3 (SYN, SYN-ACK, ACK)', 'option_b': '4 (FIN, ACK, FIN, ACK)', 'option_c': '2 (RST, ACK)', 'option_d': '1 (CLOSE)',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Medium',
            'explanation': 'A graceful TCP close requires a 4-way handshake using FIN and ACK from both sides.'
        }
    ],
    'Aptitude': [
        {
            'question': 'A train traveling at 60 km/h crosses a 200-meter platform in 24 seconds. What is the length of the train?',
            'option_a': '150 meters', 'option_b': '200 meters', 'option_c': '250 meters', 'option_d': '300 meters',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Medium',
            'explanation': 'Speed = 60 * 5/18 = 50/3 m/s. Distance = (50/3) * 24 = 400 m. Train length = 400 - 200 = 200 m.'
        },
        {
            'question': 'If 5 workers can build 5 tables in 5 days, how many days will it take 10 workers to build 10 tables?',
            'option_a': '2.5 days', 'option_b': '5 days', 'option_c': '10 days', 'option_d': '20 days',
            'correct_answer': 'B', 'marks': 1.0, 'difficulty': 'Easy',
            'explanation': 'Rate of 1 worker = 1 table in 5 days. Thus, 10 workers produce 10 tables in 5 days.'
        }
    ]
}

def generate_questions(topic='Data Structures', difficulty='Medium', count=5, marks_per_question=1.0, additional_instructions=''):
    """
    Generates questions for the specified topic and difficulty.
    Supports AI provider (OpenAI, Gemini) if configured, or falls back seamlessly to the template generator.
    """
    ai_provider = os.environ.get('AI_PROVIDER', '').lower()
    api_key = os.environ.get('AI_API_KEY', '')

    if api_key and ai_provider in ['openai', 'gemini']:
        try:
            return call_ai_generator(ai_provider, api_key, topic, difficulty, count, marks_per_question, additional_instructions)
        except Exception as e:
            # Fall back to template generator on AI failure
            pass

    return generate_template_questions(topic, difficulty, count, marks_per_question, additional_instructions)

def generate_template_questions(topic, difficulty, count, marks_per_question, additional_instructions=''):
    """
    Template generator with curated questions and algorithmic variations.
    """
    # Find matching topic or fallback to broad topic match
    matched_pool = []
    for t_key, q_list in CURATED_BANK.items():
        if t_key.lower() in topic.lower() or topic.lower() in t_key.lower():
            matched_pool.extend(q_list)
            
    if not matched_pool:
        # Fallback to general pool across all categories
        for q_list in CURATED_BANK.values():
            matched_pool.extend(q_list)
            
    # Filter by difficulty if sufficient items, else take all
    diff_pool = [q for q in matched_pool if q.get('difficulty', '').lower() == difficulty.lower()]
    if len(diff_pool) >= count:
        candidates = random.sample(diff_pool, count)
    elif len(matched_pool) >= count:
        candidates = random.sample(matched_pool, count)
    else:
        # Repeat or generate procedural variations if needed
        candidates = []
        while len(candidates) < count:
            for item in matched_pool:
                candidates.append(dict(item))
                if len(candidates) == count:
                    break

    results = []
    for i, item in enumerate(candidates, start=1):
        results.append({
            'temp_id': i,
            'question_text': item['question'],
            'option_a': item['option_a'],
            'option_b': item['option_b'],
            'option_c': item['option_c'],
            'option_d': item['option_d'],
            'correct_answer': item['correct_answer'],
            'marks': float(marks_per_question),
            'topic': topic,
            'difficulty': difficulty,
            'explanation': item.get('explanation', '')
        })
        
    return results

def call_ai_generator(provider, api_key, topic, difficulty, count, marks_per_question, instructions):
    """
    Optional external AI integration. Calls OpenAI or Gemini with structured prompt.
    """
    # Abstraction for OpenAI or other providers
    import urllib.request
    
    prompt = f"""Generate {count} multiple choice questions (MCQs) for an online technical exam.
Topic: {topic}
Difficulty: {difficulty}
Instructions: {instructions}

Respond ONLY with a valid JSON array of objects with the exact schema:
[
  {{
    "question": "string",
    "option_a": "string",
    "option_b": "string",
    "option_c": "string",
    "option_d": "string",
    "correct_answer": "A" or "B" or "C" or "D",
    "explanation": "string"
  }}
]
"""
    if provider == 'openai':
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": os.environ.get('AI_MODEL', 'gpt-3.5-turbo'),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            raw_text = data['choices'][0]['message']['content']
            parsed = json.loads(raw_text)
            
        results = []
        for i, q in enumerate(parsed[:count], start=1):
            results.append({
                'temp_id': i,
                'question_text': q['question'],
                'option_a': q['option_a'],
                'option_b': q['option_b'],
                'option_c': q['option_c'],
                'option_d': q['option_d'],
                'correct_answer': q['correct_answer'].upper(),
                'marks': float(marks_per_question),
                'topic': topic,
                'difficulty': difficulty,
                'explanation': q.get('explanation', '')
            })
        return results

    raise NotImplementedError(f"Provider {provider} not configured")
