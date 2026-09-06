import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "http://127.0.0.1:5050"

def run_live_verification():
    print("=== LIVE INTEGRATION VERIFICATION ===")

    # Setup cookie jar for candidate
    cand_cookie_jar = http.cookiejar.CookieJar()
    cand_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cand_cookie_jar))

    # Setup cookie jar for admin
    admin_cookie_jar = http.cookiejar.CookieJar()
    admin_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(admin_cookie_jar))

    # 1. Verify Home / Candidate Login Page
    with cand_opener.open(f"{BASE_URL}/") as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "TECHBLITZ" in html
        assert "Hall Ticket Number" in html
        assert "Team ID" in html
        print("[✓] Step 1: Candidate Login page accessible and rendered correctly.")

    # 2. Test Invalid Candidate Login (Rejected by DB access control)
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/login",
        data=json.dumps({"hall_ticket_number": "UNKNOWN", "name": "Fake User", "team_id": "TEAM01"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        cand_opener.open(req)
        assert False, "Should have been rejected"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        err_data = json.loads(e.read().decode('utf-8'))
        assert "not registered" in err_data['error']
        print("[✓] Step 2: Unregistered candidate correctly rejected (HTTP 403 Access Denied).")

    # 3. Test Invalid Team ID for Valid Hall Ticket
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/login",
        data=json.dumps({"hall_ticket_number": "TB001", "name": "Rahul", "team_id": "TEAM99"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        cand_opener.open(req)
        assert False, "Should have been rejected"
    except urllib.error.HTTPError as e:
        assert e.code == 403
        err_data = json.loads(e.read().decode('utf-8'))
        assert "do not match" in err_data['error']
        print("[✓] Step 3: Team mismatch correctly rejected (HTTP 403).")

    # 4. Valid Candidate Login (TB002 - Priya)
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/login",
        data=json.dumps({"hall_ticket_number": "TB002", "name": "Priya", "team_id": "TEAM01"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with cand_opener.open(req) as resp:
        assert resp.status == 200
        cand_data = json.loads(resp.read().decode('utf-8'))
        assert cand_data['success'] is True
        print(f"[✓] Step 4: Registered Candidate verified successfully: {cand_data['candidate_id']}")

    # 5. Access Instructions Page
    with cand_opener.open(f"{BASE_URL}/instructions") as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "IMPORTANT TEST INSTRUCTIONS" in html
        assert "Violations Allowed: 3" in html
        print("[✓] Step 5: Instructions page rendered with proctoring rules.")

    # 6. Start Test Session
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/start",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    with cand_opener.open(req) as resp:
        assert resp.status == 200
        start_data = json.loads(resp.read().decode('utf-8'))
        assert start_data['status'] == 'ACTIVE'
        assert 1150 <= start_data['remaining_seconds'] <= 1200
        print(f"[✓] Step 6: Test started, 20-minute server timer active: {start_data['remaining_seconds']}s remaining.")

    # 7. Fetch Exam Questions
    with cand_opener.open(f"{BASE_URL}/api/candidate/questions") as resp:
        assert resp.status == 200
        q_data = json.loads(resp.read().decode('utf-8'))
        assert q_data['success'] is True
        assert len(q_data['questions']) == 15
        # Verify correct answers are NOT leaked to the client!
        for q in q_data['questions']:
            assert 'correct_answer' not in q
            assert 'explanation' not in q
        print(f"[✓] Step 7: 15 MCQs fetched securely without exposing correct answers.")

    # 8. Answer First 3 Questions
    for idx in range(3):
        q = q_data['questions'][idx]
        req = urllib.request.Request(
            f"{BASE_URL}/api/candidate/answer",
            data=json.dumps({"question_id": q['id'], "selected_answer": "B", "current_question_index": idx}).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with cand_opener.open(req) as resp:
            assert resp.status == 200
    print("[✓] Step 8: Candidate answers successfully recorded.")

    # 9. Trigger Proctoring Violation (Tab Switch)
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/violations",
        data=json.dumps({"type": "TAB_SWITCH", "metadata": {"reason": "Switched tab"}}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with cand_opener.open(req) as resp:
        assert resp.status == 200
        v_data = json.loads(resp.read().decode('utf-8'))
        assert v_data['violation_count'] == 1
        assert v_data['warning_active'] is True
        assert v_data['warning_seconds_left'] == 20
        print("[✓] Step 9: TAB_SWITCH violation recorded, 20-second warning countdown initiated.")

    # 10. Acknowledge Warning Within 20 Seconds
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/acknowledge",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    with cand_opener.open(req) as resp:
        assert resp.status == 200
        ack_data = json.loads(resp.read().decode('utf-8'))
        assert ack_data['success'] is True
        assert ack_data['status'] == 'ACTIVE'
        print("[✓] Step 10: 20-second warning acknowledged, candidate returned to ACTIVE status.")

    # 11. Submit Assessment
    req = urllib.request.Request(
        f"{BASE_URL}/api/candidate/submit",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    with cand_opener.open(req) as resp:
        assert resp.status == 200
        sub_data = json.loads(resp.read().decode('utf-8'))
        assert sub_data['success'] is True
        assert sub_data['redirect'] == '/result'
        assert 'score' not in sub_data, "Score must NOT be returned to candidate"
        print("[✓] Step 11: Assessment submitted successfully. Score hidden from candidate response.")

    # 12. View Results Page (Score must NOT be visible to candidate!)
    with cand_opener.open(f"{BASE_URL}/result") as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "TEST SUBMITTED SUCCESSFULLY" in html
        assert "RESPONSES RECORDED & SECURED" in html
        assert "Your Final Score" not in html
        print("[✓] Step 12: Candidate results page rendered with score hidden.")

    # 13. Admin Login
    req = urllib.request.Request(
        f"{BASE_URL}/api/admin/login",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with admin_opener.open(req) as resp:
        assert resp.status == 200
        adm_data = json.loads(resp.read().decode('utf-8'))
        assert adm_data['success'] is True
        print("[✓] Step 13: Admin authenticated successfully.")

    # 14. Admin Live Polling API
    with admin_opener.open(f"{BASE_URL}/api/admin/live") as resp:
        assert resp.status == 200
        live_data = json.loads(resp.read().decode('utf-8'))
        assert live_data['success'] is True
        assert live_data['counters']['completed'] >= 1
        assert len(live_data['violations_feed']) >= 1
        assert len(live_data['results']) >= 1
        print(f"[✓] Step 14: Admin Live API verified: {live_data['counters']['completed']} completed, {len(live_data['violations_feed'])} violations in feed.")

    # 15. Admin Download Excel Results
    with admin_opener.open(f"{BASE_URL}/api/admin/export/excel") as resp:
        assert resp.status == 200
        assert resp.headers.get('Content-Type') == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        excel_bytes = resp.read()
        assert len(excel_bytes) > 1000
        print(f"[✓] Step 15: Admin exported TECHBLITZ_RESULTS.xlsx ({len(excel_bytes)} bytes) successfully.")

    print("\n========================================================")
    print("ALL 15 END-TO-END LIVE WORKFLOW STEPS VERIFIED WITH 100% SUCCESS!")
    print("========================================================")

if __name__ == '__main__':
    run_live_verification()
