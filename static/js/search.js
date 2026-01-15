function filterExams() {
    const input = document.getElementById("searchExam");
    const filter = input.value.toLowerCase();
    const exams = document.querySelectorAll(".exam-card");

    exams.forEach(exam => {
        const text = exam.textContent.toLowerCase();
        exam.style.display = text.includes(filter) ? "block" : "none";
    });
}