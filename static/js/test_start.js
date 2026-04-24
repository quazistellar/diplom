const totalQuestions = parseInt(document.querySelector('.questions-list')?.dataset.totalQuestions || 0);
const testId = parseInt(document.querySelector('meta[name="test-id"]')?.content || 0);

let currentQuestion = 0;
let answeredQuestions = new Set();
let userAnswers = {};

const sessionId = `test_session_${testId}_${Date.now()}`;

let startTime = null;
let timerInterval = null;
let timeSpent = 0;

/// функция запуска таймера теста
function startTimer() {
    startTime = Date.now();
    timeSpent = 0;
    updateTimerDisplay();
    timerInterval = setInterval(updateTimerDisplay, 1000);
}

/// функция обновления отображения таймера
function updateTimerDisplay() {
    if (!startTime) return;
    
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    timeSpent = elapsed;
    
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    
    const timerDisplay = document.getElementById('timerDisplay');
    if (timerDisplay) {
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

/// функция остановки таймера теста
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

/// функция получения затраченного времени в секундах
function getTimeSpent() {
    if (!startTime) return 0;
    return Math.floor((Date.now() - startTime) / 1000);
}

/// функция открытия модального окна
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
    }
}

/// функция закрытия модального окна
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    closeModal('confirmModal');
    closeModal('resultModal');
    
    startTimer();
    showQuestion(0);
    initEventListeners();
    loadSavedAnswers();
});

/// функция отображения вопроса по индексу
function showQuestion(index) {
    const allQuestions = document.querySelectorAll('.question-card');
    if (index < 0) index = 0;
    if (index >= totalQuestions) index = totalQuestions - 1;
    
    allQuestions.forEach((q, i) => {
        q.classList.toggle('active', i === index);
    });
    
    currentQuestion = index;
    
    const prevBtn = document.getElementById('prevQuestion');
    const nextBtn = document.getElementById('nextQuestion');
    const submitBtn = document.getElementById('submitTest');
    
    if (prevBtn) prevBtn.style.display = index > 0 ? 'inline-flex' : 'none';
    if (nextBtn) nextBtn.style.display = index < totalQuestions - 1 ? 'inline-flex' : 'none';
    if (submitBtn) submitBtn.style.display = index === totalQuestions - 1 ? 'inline-flex' : 'none';
    
    document.querySelectorAll('.nav-question').forEach((btn, i) => {
        btn.classList.toggle('current', i === index);
    });
}

/// функция сохранения ответа на вопрос
function saveAnswer(questionIndex) {
    const questionCard = document.getElementById(`question-${questionIndex}`);
    if (!questionCard) return;
    
    const questionId = questionCard.dataset.questionId;
    
    const radioSelected = questionCard.querySelector('input[type="radio"]:checked');
    if (radioSelected) {
        userAnswers[questionId] = radioSelected.value;
        answeredQuestions.add(questionIndex);
        updateProgress();
        updateNavigation();
        saveToLocalStorage();
        return;
    }
    
    const checkboxes = questionCard.querySelectorAll('input[type="checkbox"]:checked');
    if (checkboxes.length > 0) {
        userAnswers[questionId] = Array.from(checkboxes).map(cb => cb.value);
        answeredQuestions.add(questionIndex);
        updateProgress();
        updateNavigation();
        saveToLocalStorage();
        return;
    }

    const textarea = questionCard.querySelector('textarea');
    if (textarea && textarea.value.trim()) {
        userAnswers[questionId] = textarea.value.trim();
        answeredQuestions.add(questionIndex);
        updateProgress();
        updateNavigation();
        saveToLocalStorage();
        return;
    }

    const selects = questionCard.querySelectorAll('.matching-select');
    if (selects.length > 0) {
        const matchingAnswers = {};
        let hasValue = false;
        selects.forEach(select => {
            if (select.value) {
                matchingAnswers[select.name] = select.value;
                hasValue = true;
            }
        });
        if (hasValue) {
            userAnswers[questionId] = matchingAnswers;
            answeredQuestions.add(questionIndex);
        } else {
            delete userAnswers[questionId];
            answeredQuestions.delete(questionIndex);
        }
        updateProgress();
        updateNavigation();
        saveToLocalStorage();
        return;
    }
    
    delete userAnswers[questionId];
    answeredQuestions.delete(questionIndex);
    updateProgress();
    updateNavigation();
    saveToLocalStorage();
}

/// функция обновления прогресса ответов
function updateProgress() {
    const answered = answeredQuestions.size;
    const percent = totalQuestions > 0 ? Math.round((answered / totalQuestions) * 100) : 0;
    
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const answeredCount = document.getElementById('answeredCount');
    
    if (progressFill) progressFill.style.width = `${percent}%`;
    if (progressPercent) progressPercent.textContent = `${percent}%`;
    if (answeredCount) answeredCount.textContent = answered;
}

/// функция обновления навигации по вопросам
function updateNavigation() {
    document.querySelectorAll('.nav-question').forEach((btn, i) => {
        btn.classList.toggle('answered', answeredQuestions.has(i));
    });
}

/// функция сохранения ответов в localStorage
function saveToLocalStorage() {
    const data = {
        answers: userAnswers,
        timestamp: Date.now()
    };
    localStorage.setItem(sessionId, JSON.stringify(data));
}

/// функция загрузки сохранённых ответов из localStorage
function loadSavedAnswers() {
    const saved = localStorage.getItem(sessionId);
    if (saved) {
        try {
            const data = JSON.parse(saved);
            userAnswers = data.answers || {};
            
            for (const [qId, answer] of Object.entries(userAnswers)) {
                const questionCard = document.querySelector(`.question-card[data-question-id="${qId}"]`);
                if (questionCard) {
                    if (Array.isArray(answer)) {
                        answer.forEach(val => {
                            const cb = questionCard.querySelector(`input[type="checkbox"][value="${val}"]`);
                            if (cb) cb.checked = true;
                        });
                    } else if (typeof answer === 'object' && answer !== null) {
                        for (const [name, val] of Object.entries(answer)) {
                            const select = questionCard.querySelector(`select[name="${name}"]`);
                            if (select) select.value = val;
                        }
                    } else {
                        const radio = questionCard.querySelector(`input[type="radio"][value="${answer}"]`);
                        if (radio) radio.checked = true;
                        const textarea = questionCard.querySelector('textarea');
                        if (textarea) textarea.value = answer;
                    }
                }
            }
            
            for (let i = 0; i < totalQuestions; i++) {
                const qCard = document.getElementById(`question-${i}`);
                if (qCard) {
                    const qId = qCard.dataset.questionId;
                    if (userAnswers[qId]) answeredQuestions.add(i);
                }
            }
            updateProgress();
            updateNavigation();
        } catch(e) {
            console.error('Error loading saved answers:', e);
        }
    }
}

/// функция инициализации всех обработчиков событий
function initEventListeners() {
    const prevBtn = document.getElementById('prevQuestion');
    const nextBtn = document.getElementById('nextQuestion');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentQuestion > 0) showQuestion(currentQuestion - 1);
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentQuestion < totalQuestions - 1) showQuestion(currentQuestion + 1);
        });
    }

    document.querySelectorAll('.nav-question').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.questionIndex);
            if (!isNaN(index)) showQuestion(index);
        });
    });
    
    document.querySelectorAll('.question-card').forEach((card, idx) => {
        const inputs = card.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('change', () => saveAnswer(idx));
            if (input.tagName === 'TEXTAREA') {
                input.addEventListener('input', () => saveAnswer(idx));
            }
        });
    });
    
    const submitBtn = document.getElementById('submitTest');
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            openModal('confirmModal');
        });
    }
    
    const cancelBtn = document.getElementById('cancelSubmit');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => closeModal('confirmModal'));
    }
    
    const confirmBtn = document.getElementById('confirmSubmit');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', submitTest);
    }
    
    const closeResultBtn = document.getElementById('closeResultModal');
    if (closeResultBtn) {
        closeResultBtn.addEventListener('click', () => {
            closeModal('resultModal');
            stopTimer();
            localStorage.removeItem(sessionId);
            const backBtn = document.getElementById('backToCourseBtn');
            if (backBtn) window.location.href = backBtn.href;
        });
    }
    
    const confirmModal = document.getElementById('confirmModal');
    const resultModal = document.getElementById('resultModal');
    
    if (confirmModal) {
        confirmModal.addEventListener('click', function(e) {
            if (e.target === this) closeModal('confirmModal');
        });
    }
    
    if (resultModal) {
        resultModal.addEventListener('click', function(e) {
            if (e.target === this) closeModal('resultModal');
        });
    }
}

/// функция отправки теста на сервер
function submitTest() {
    closeModal('confirmModal');
    
    const timeSpentValue = getTimeSpent();
    
    const confirmBtn = document.getElementById('confirmSubmit');
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
    }
    
    // получение CSRF-токена из cookie
    function getCSRFToken() {
        let cookieValue = null;
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                cookieValue = cookie.substring('csrftoken='.length);
                break;
            }
        }
        return cookieValue;
    }
    
    fetch(`/listener/test/${testId}/submit/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            answers: userAnswers,
            time_spent: timeSpentValue
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.removeItem(sessionId);
            stopTimer();
            showResultModal(data);
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Завершить';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка при отправке теста');
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Завершить';
        }
    });
}

/// функция отображения модального окна с результатами теста
function showResultModal(data) {
    const resultContent = document.getElementById('resultContent');
    if (!resultContent) return;
    
    const minutes = Math.floor(timeSpent / 60);
    const seconds = timeSpent % 60;
    const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    let html = '';
    
    // отображение для балльной системы оценки
    if (data.grading_form === 'points') {
        let bestStatusHtml = '';
        if (data.best_passed && data.best_passed !== data.passed) {
            bestStatusHtml = `<div style="background: rgba(46,204,113,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-trophy" style="color: #f1c40f;"></i> 
                <strong>Ваш лучший результат: ${data.best_score}/${data.max_score} баллов (ЗАЧТЕНО)</strong>
                <br><small>Статус теста не изменится, так как у вас уже есть зачётная попытка</small>
            </div>`;
        } else if (data.best_passed && data.passed) {
            bestStatusHtml = `<div style="background: rgba(46,204,113,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-check-circle" style="color: #2ecc71;"></i> 
                <strong>Тест успешно сдан!</strong>
            </div>`;
        } else if (!data.best_passed && data.passed) {
            bestStatusHtml = `<div style="background: rgba(46,204,113,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-check-circle" style="color: #2ecc71;"></i> 
                <strong>Поздравляем! Вы сдали тест!</strong>
            </div>`;
        } else {
            bestStatusHtml = `<div style="background: rgba(231,76,60,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-times-circle" style="color: #e74c3c;"></i> 
                <strong>Тест не сдан. Попробуйте ещё раз.</strong>
            </div>`;
        }
        
        html = `
            <div class="result-score-large ${data.passed ? 'result-passed' : 'result-failed'}">${data.score}/${data.max_score}</div>
            <p style="margin: 10px 0;">Вы набрали ${data.score} из ${data.max_score} возможных баллов</p>
            <p style="margin: 10px 0;">Проходной балл: ${data.passing_score}</p>
            <p style="margin: 10px 0;"><i class="fas fa-clock"></i> Время выполнения: ${timeString}</p>
            ${bestStatusHtml}
        `;
    } 
    // отображение для системы зачёт/незачёт
    else {
        let bestStatusHtml = '';
        if (data.best_passed && data.best_passed !== data.passed) {
            bestStatusHtml = `<div style="background: rgba(46,204,113,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-trophy" style="color: #f1c40f;"></i> 
                <strong>У вас уже есть ЗАЧЁТ по этому тесту!</strong>
                <br><small>Статус теста остаётся "Зачтено"</small>
            </div>`;
        } else if (data.best_passed && data.passed) {
            bestStatusHtml = `<div style="background: rgba(46,204,113,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-check-circle" style="color: #2ecc71;"></i> 
                <strong>Тест зачтён!</strong>
            </div>`;
        } else if (!data.best_passed && data.passed) {
            bestStatusHtml = `<div style="background: rgba(46,204,113,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-check-circle" style="color: #2ecc71;"></i> 
                <strong>Поздравляем! Тест зачтён!</strong>
            </div>`;
        } else {
            bestStatusHtml = `<div style="background: rgba(231,76,60,0.15); padding: 15px; border-radius: 16px; margin-top: 15px;">
                <i class="fas fa-times-circle" style="color: #e74c3c;"></i> 
                <strong>Тест не зачтён. Попробуйте ещё раз.</strong>
            </div>`;
        }
        
        html = `
            <div class="result-score-large ${data.passed ? 'result-passed' : 'result-failed'}">${data.passed ? 'ЗАЧЁТ' : 'НЕЗАЧЁТ'}</div>
            <p style="margin: 10px 0;">${data.passed ? 'Поздравляем! Эта попытка успешна.' : 'К сожалению, эта попытка не зачтена.'}</p>
            <p style="margin: 10px 0;"><i class="fas fa-clock"></i> Время выполнения: ${timeString}</p>
            ${bestStatusHtml}
        `;
    }
    
    resultContent.innerHTML = html;
    openModal('resultModal');
}