import os
import re

from playwright.sync_api import Page

LOGIN_URL = "https://edux.cmcu.edu.vn/login"
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
ANSWER_CARD_SELECTOR = (
    "div.flex.items-center.space-x-6.p-8.rounded-xl.border-2."
    "transition-colors.cursor-pointer.min-h-\\[80px\\]"
)
PROGRESS_RE = re.compile(r"Tiến độ:\s*(\d+)\s*/\s*(\d+)\s*câu đúng", re.IGNORECASE)
CORRECT_ANSWER_RE = re.compile(r"Đáp án đúng\s*:\s*([A-D])\.\s*([^\r\n]+)", re.IGNORECASE)
SLIDE_POSITION_RE = re.compile(r"(?m)^\s*(\d+)\s*/\s*(\d+)\s*$")


def load_env_file() -> None:
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r", encoding="utf-8") as env_file:
        for line in env_file:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            if key and key not in os.environ:
                os.environ[key] = value


def ensure_login_env() -> tuple[str, str]:
    if os.environ.get("USE_MICROSOFT_LOGIN") == "1":
        return "", ""

    load_env_file()
    email = os.environ.get("EDUX_EMAIL", "").strip()
    password = os.environ.get("EDUX_PASSWORD", "").strip()

    if not email:
        email = input("Enter EDUX email: ").strip()
    if not password:
        password = input("Enter EDUX password: ").strip()

    os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as env_file:
        env_file.write(f"EDUX_EMAIL={email}\n")
        env_file.write(f"EDUX_PASSWORD={password}\n")

    os.environ["EDUX_EMAIL"] = email
    os.environ["EDUX_PASSWORD"] = password
    return email, password


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def is_visible(locator) -> bool:
    try:
        return locator.is_visible()
    except Exception:
        return False


def is_visible_and_enabled(locator) -> bool:
    try:
        return locator.is_visible() and locator.is_enabled()
    except Exception:
        return False


def extract_answers(answers_locator) -> list[dict[str, str]]:
    """Return each answer card in the same order as the rendered EDUX UI."""
    return answers_locator.evaluate_all(
        """
        nodes => nodes.map(node => {
            const letter = node.querySelector('span.font-bold')?.innerText?.trim() || '';
            const text = node.querySelector('div.prose p')?.innerText?.trim() || node.innerText?.trim() || '';
            return { letter, text, fullText: `${letter} ${text}`.trim() };
        })
        """
    )


def wait_for_screen_change(page: Page, previous_body: str, timeout: int = 10_000) -> bool:
    """Wait for an action to update the visible lesson/question UI."""
    try:
        page.wait_for_function(
            "previousBody => document.body && document.body.innerText !== previousBody",
            previous_body,
            timeout=timeout,
        )
        return True
    except Exception:
        return False


def click_and_wait(page: Page, button, action: str) -> bool:
    previous_body = page.locator("body").inner_text()
    button.click()
    print(f"[INFO] Clicked '{action}'.")
    return wait_for_screen_change(page, previous_body)


def progress_from_page(page: Page) -> tuple[int, int] | None:
    match = PROGRESS_RE.search(page.locator("body").inner_text())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def slide_position_from_page(page: Page) -> tuple[int, int] | None:
    """Read the lesson pager (for example, '27 / 27') when it is visible."""
    match = SLIDE_POSITION_RE.search(page.locator("body").inner_text())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def advance_to_next_slide(page: Page, next_page_button) -> bool:
    """Click next slide and confirm that the UI actually moved forward.

    EDUX may leave a green 'Trang sau' button on the final question even though
    there is no subsequent slide. Treating an unchanged screen as completion
    prevents the main loop from attempting the same completed question again.
    """
    previous_body = page.locator("body").inner_text()
    previous_position = slide_position_from_page(page)
    next_page_button.click()
    print("[INFO] Clicked 'Trang sau'.")

    if not wait_for_screen_change(page, previous_body, timeout=5_000):
        if previous_position and previous_position[0] >= previous_position[1]:
            print(f"[INFO] Reached final slide ({previous_position[0]}/{previous_position[1]}).")
        else:
            print("[INFO] 'Trang sau' did not change the UI. Treating the lesson as complete.")
        return False

    current_position = slide_position_from_page(page)
    if previous_position and current_position == previous_position:
        print("[WARN] 'Trang sau' changed the UI but did not advance the slide number. Stopping to avoid a loop.")
        return False
    return True


def correct_answer_from_feedback(page: Page, answers: list[dict[str, str]]) -> str | None:
    """Read the answer shown after an incorrect attempt and map it to an answer card."""
    body_text = page.locator("body").inner_text()
    match = CORRECT_ANSWER_RE.search(body_text)
    if match:
        letter = f"{match.group(1).upper()}."
        for answer in answers:
            if answer["letter"].upper().startswith(letter):
                return answer["fullText"]

    # EDUX also marks the correct card green. This fallback covers layout changes
    # where the feedback block does not keep the answer on the same text line.
    green_indices = page.locator(ANSWER_CARD_SELECTOR).evaluate_all(
        """
        nodes => nodes
          .map((node, index) => ({ index, classes: String(node.className || '') }))
          .filter(item => /(?:border|bg|text)-green/i.test(item.classes))
          .map(item => item.index)
        """
    )
    if green_indices:
        return answers[green_indices[0]]["fullText"]
    return None


def answer_index_to_click(
    answers: list[dict[str, str]],
    learned_answer: str | None,
    attempted_answers: set[str],
) -> int | None:
    """Prefer a learned answer; otherwise choose the longest untried answer."""
    if learned_answer:
        learned_normalized = normalize_text(learned_answer)
        for index, answer in enumerate(answers):
            if normalize_text(answer["fullText"]) == learned_normalized:
                return index

    candidates = [
        (index, answer)
        for index, answer in enumerate(answers)
        if normalize_text(answer["fullText"]) not in attempted_answers
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: len(item[1]["text"].strip()))[0]


def test_wait_for_user_login(page: Page) -> None:
    email, password = ensure_login_env()
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    
    if os.environ.get("USE_MICROSOFT_LOGIN") == "1":
        print("\n[INFO] Selecting Microsoft Login...")
        microsoft_btn = page.locator("button:has-text('Microsoft'), a:has-text('Microsoft'), button:has-text('microsoft'), a:has-text('microsoft')").first
        try:
            microsoft_btn.click(timeout=3000)
        except Exception:
            pass
        print("[INFO] Please complete the Microsoft login in the browser window.")
    else:
        page.locator("#email").fill(email)
        page.locator("#password").fill(password)
        page.locator("#password").press("Enter")
        print("\n[INFO] Auto-login attempted. If needed, finish any extra steps in the browser.")
    
    while True:
        print("\n[INFO] Navigate to the quiz screen.")
        print("[INFO] Press Enter here to start/continue answering. Type 'q' and Enter to quit.")
        user_input = input()
        if user_input.strip().lower() == 'q':
            break

        # These caches last for the current lesson run. A retry can therefore use
        # the correct answer that EDUX has just revealed without guessing again.
        learned_answers: dict[str, str] = {}
        attempted_answers: dict[str, set[str]] = {}

        no_question_button = page.get_by_role("button", name="Không có câu hỏi", exact=True)
        answer_button = page.get_by_role("button", name="Trả lời trên lớp", exact=True)
        check_button = page.get_by_role("button", name="Kiểm tra", exact=True)
        next_button = page.get_by_role("button", name="Câu tiếp theo", exact=True)
        retry_button = page.get_by_role("button", name="Thử lại", exact=True)
        next_page_button = page.get_by_role("button", name="Trang sau", exact=True)
        question_locator = page.locator("p.my-3.text-gray-800.leading-relaxed").first
        answers_locator = page.locator(ANSWER_CARD_SELECTOR)

        while not page.is_closed():
            # A lesson slide without a question has no question text, only the
            # disabled-looking 'Không có câu hỏi' indicator and 'Trang sau'.
            if is_visible(no_question_button):
                if is_visible_and_enabled(next_page_button):
                    if not advance_to_next_slide(page, next_page_button):
                        break
                    print("[INFO] No question on this slide. Clicked 'Trang sau'.")
                else:
                    print("[INFO] No question and 'Trang sau' is disabled. Possibly end of slides.")
                    break
                continue

            # This is the normal lesson-screen entry point.
            if not is_visible(question_locator):
                try:
                    answer_button.wait_for(state="visible", timeout=3000)
                    click_and_wait(page, answer_button, "Trả lời trên lớp")
                    continue
                except Exception:
                    print("[WARN] 'Trả lời trên lớp' button not found. Assuming you aren't on the quiz slide yet. Prompting again.")
                    break

            try:
                question_locator.wait_for(state="visible", timeout=10000)
            except Exception:
                print("[WARN] Question not visible yet. Retrying loop.")
                page.wait_for_timeout(200)
                continue

            question_text = question_locator.inner_text().strip()
            question_key = normalize_text(question_text)
            print(f"[INFO] Question: {question_text}")

            try:
                answers_locator.first.wait_for(state="visible", timeout=10000)
            except Exception:
                print("[WARN] Answers not visible yet. Retrying loop.")
                page.wait_for_timeout(200)
                continue

            answers = extract_answers(answers_locator)
            answer_count = len(answers)
            print(f"[INFO] Answers found: {answer_count}")

            if not answer_count:
                print("[WARN] No answers available to click.")
                break

            chosen_index = answer_index_to_click(
                answers,
                learned_answers.get(question_key),
                attempted_answers.setdefault(question_key, set()),
            )
            if chosen_index is None:
                print("[WARN] All answers were attempted but no correct answer could be extracted. Stopping to avoid a loop.")
                break

            chosen_answer = answers[chosen_index]["fullText"]
            if question_key in learned_answers:
                print(f"[INFO] Using learned answer: {chosen_answer}")
            else:
                print(f"[INFO] No learned answer. Choosing longest option: {chosen_answer}")

            answers_locator.nth(chosen_index).click()
            try:
                page.wait_for_function(
                    """
                    () => {
                      const button = Array.from(document.querySelectorAll('button'))
                        .find(item => (item.textContent || '').trim() === 'Kiểm tra');
                      return button && !button.disabled;
                    }
                    """,
                    timeout=5000,
                )
                click_and_wait(page, check_button, "Kiểm tra")
            except Exception:
                print("[WARN] 'Kiểm tra' did not become available after selecting an answer.")
                continue

            try:
                page.wait_for_function(
                    """
                    () => ['Trang sau', 'Câu tiếp theo', 'Thử lại'].some(label => {
                      const button = Array.from(document.querySelectorAll('button'))
                        .find(item => (item.textContent || '').trim() === label);
                      return button && !button.disabled && button.offsetParent !== null;
                    })
                    """,
                    timeout=10000,
                )
            except Exception:
                print("[WARN] No result action appeared after checking the answer.")
                continue

            if is_visible_and_enabled(retry_button):
                correct_answer = correct_answer_from_feedback(page, answers)
                attempted_answers[question_key].add(normalize_text(chosen_answer))
                if correct_answer:
                    learned_answers[question_key] = correct_answer
                    print(f"[INFO] Learned correct answer: {correct_answer}")
                else:
                    print("[WARN] Wrong answer detected but could not read the correct answer; trying another option.")
                click_and_wait(page, retry_button, "Thử lại")
                continue

            # Some single-question slides do not render the progress text. The
            # visible follow-up button is therefore the authoritative signal.
            if is_visible_and_enabled(next_page_button):
                if not advance_to_next_slide(page, next_page_button):
                    break
                progress = progress_from_page(page)
                if progress:
                    print(f"[INFO] Slide complete ({progress[0]}/{progress[1]}).")
                else:
                    print("[INFO] Slide complete. No progress text was displayed.")
            elif is_visible_and_enabled(next_button):
                click_and_wait(page, next_button, "Câu tiếp theo")
                progress = progress_from_page(page)
                if progress:
                    print(f"[INFO] Continuing slide progress ({progress[0]}/{progress[1]}).")
                else:
                    print("[INFO] Continuing to the next question.")
            else:
                print("[WARN] Answer was accepted, but no follow-up button was available. Stopping.")
                break

        if page.is_closed():
            break

        print(f"[INFO] Current URL: {page.url}")
