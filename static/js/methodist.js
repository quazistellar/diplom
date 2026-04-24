// функция для отображения кастомного уведомления
function showNotification(message, type = 'error') {
    let messagesContainer = document.querySelector('.messages-container');
    
    if (!messagesContainer) {
        messagesContainer = document.createElement('div');
        messagesContainer.className = 'messages-container container mt-3';
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.insertBefore(messagesContainer, mainContent.firstChild);
        } else {
            document.body.insertBefore(messagesContainer, document.body.firstChild);
        }
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    if (type === 'error') iconClass = 'fa-exclamation-circle';
    if (type === 'warning') iconClass = 'fa-exclamation-triangle';
    
    alertDiv.innerHTML = `
        <i class="fas ${iconClass}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    messagesContainer.appendChild(alertDiv);
    
    setTimeout(function() {
        alertDiv.style.opacity = '0';
        alertDiv.style.transform = 'translateY(-10px)';
        setTimeout(function() {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 300);
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    const messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            setTimeout(function() {
                if (message.parentNode) {
                    message.remove();
                }
            }, 300);
        }, 5000);
    });
});

// фукнция подтверждения удаления с кастомным модальным окном
function confirmDelete(event, itemName) {
    event.preventDefault();
    
    const modal = document.createElement('div');
    modal.className = 'methodist-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    modal.innerHTML = `
        <div class="methodist-modal-content" style="
            background: var(--surface);
            border-radius: var(--radius);
            max-width: 450px;
            width: 90%;
            padding: 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease;
        ">
            <i class="fas fa-exclamation-triangle" style="font-size: 64px; color: #f1c40f; margin-bottom: 20px;"></i>
            <h3 style="color: var(--text); margin-bottom: 15px;">Подтверждение удаления</h3>
            <p style="color: var(--text-soft); margin-bottom: 10px;">Вы уверены, что хотите удалить</p>
            <strong style="color: var(--primary); font-size: 18px; display: block; margin: 15px 0;">"${itemName}"</strong>
            <p style="color: var(--text-soft); font-size: 14px;">Это действие нельзя отменить.</p>
            <div style="display: flex; gap: 15px; justify-content: center; margin-top: 25px;">
                <button class="methodist-btn methodist-btn-secondary" id="cancel-delete" style="padding: 10px 24px;">Отмена</button>
                <button class="methodist-btn methodist-btn-danger" id="confirm-delete" style="padding: 10px 24px;">Удалить</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const cancelBtn = modal.querySelector('#cancel-delete');
    const confirmBtn = modal.querySelector('#confirm-delete');
    
    cancelBtn.addEventListener('click', function() {
        modal.remove();
    });
    
    confirmBtn.addEventListener('click', function() {
        modal.remove();
        if (event.target.tagName === 'A') {
            window.location.href = event.target.href;
        } else if (event.target.form) {
            event.target.form.submit();
        }
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    return false;
}

// функция валидации формы курса
function validateCourseForm(event) {
    const courseName = document.querySelector('input[name="course_name"]');
    const courseHours = document.querySelector('input[name="course_hours"]');
    
    if (courseName && courseName.value.trim().length < 3) {
        showNotification('Название курса должно содержать минимум 3 символа', 'error');
        courseName.focus();
        event.preventDefault();
        return false;
    }
    
    if (courseHours && courseHours.value && parseInt(courseHours.value) <= 0) {
        showNotification('Количество часов должно быть положительным числом', 'error');
        courseHours.focus();
        event.preventDefault();
        return false;
    }
    
    return true;
}

// функция валидации формы лекции
function validateLectureForm(event) {
    const lectureName = document.querySelector('input[name="lecture_name"]');
    const lectureContent = document.querySelector('textarea[name="lecture_content"]');
    const lectureOrder = document.querySelector('input[name="lecture_order"]');
    
    if (lectureName && lectureName.value.trim().length < 3) {
        showNotification('Название лекции должно содержать минимум 3 символа', 'error');
        lectureName.focus();
        event.preventDefault();
        return false;
    }
    
    if (lectureContent && lectureContent.value.trim().length < 50) {
        showNotification('Содержание лекции должно содержать минимум 50 символов', 'error');
        lectureContent.focus();
        event.preventDefault();
        return false;
    }
    
    if (lectureOrder && lectureOrder.value && parseInt(lectureOrder.value) <= 0) {
        showNotification('Порядок лекции должен быть положительным числом', 'error');
        lectureOrder.focus();
        event.preventDefault();
        return false;
    }
    
    return true;
}

// функция валидации формы практического задания
function validateAssignmentForm(event) {
    const assignmentName = document.querySelector('input[name="practical_assignment_name"]');
    const assignmentDesc = document.querySelector('textarea[name="practical_assignment_description"]');
    const gradingType = document.querySelector('select[name="grading_type"]');
    const maxScore = document.querySelector('input[name="max_score"]');
    
    if (assignmentName && assignmentName.value.trim().length < 3) {
        showNotification('Название задания должно содержать минимум 3 символа', 'error');
        assignmentName.focus();
        event.preventDefault();
        return false;
    }
    
    if (assignmentDesc && assignmentDesc.value.trim().length < 20) {
        showNotification('Описание задания должно содержать минимум 20 символов', 'error');
        assignmentDesc.focus();
        event.preventDefault();
        return false;
    }
    
    if (gradingType && gradingType.value === 'points') {
        if (!maxScore || !maxScore.value || parseInt(maxScore.value) <= 0) {
            showNotification('Для балльной системы необходимо указать максимальный балл', 'error');
            if (maxScore) maxScore.focus();
            event.preventDefault();
            return false;
        }
    }
    
    return true;
}

// функции валидации формы теста
function validateTestForm(event) {
    const testName = document.querySelector('input[name="test_name"]');
    const gradingForm = document.querySelector('select[name="grading_form"]');
    const passingScore = document.querySelector('input[name="passing_score"]');
    const lecture = document.querySelector('select[name="lecture"]');
    
    if (testName && testName.value.trim().length < 3) {
        showNotification('Название теста должно содержать минимум 3 символа', 'error');
        testName.focus();
        event.preventDefault();
        return false;
    }
    
    if (lecture && (!lecture.value || lecture.value === '')) {
        showNotification('Пожалуйста, выберите лекцию для теста', 'error');
        lecture.focus();
        event.preventDefault();
        return false;
    }

    if (gradingForm && gradingForm.value === 'points') {
        if (!passingScore || !passingScore.value || parseInt(passingScore.value) < 0) {
            showNotification('Для формы оценки "По баллам" необходимо указать проходной балл', 'error');
            if (passingScore) passingScore.focus();
            event.preventDefault();
            return false;
        }
    }
    
    return true;
}

document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (form.querySelector('input[name="course_name"]')) {
            form.addEventListener('submit', validateCourseForm);
        }
        else if (form.querySelector('textarea[name="lecture_content"]')) {
            form.addEventListener('submit', validateLectureForm);
        }
        else if (form.querySelector('textarea[name="practical_assignment_description"]')) {
            form.addEventListener('submit', validateAssignmentForm);
        }
        else if (form.querySelector('select[name="grading_form"]')) {
            form.addEventListener('submit', validateTestForm);
        }
    });
    
    const gradingForm = document.querySelector('select[name="grading_form"]');
    const passingScoreField = document.getElementById('passing-score-field');
    if (gradingForm && passingScoreField) {
        function togglePassingScoreField() {
            const passingScoreGroup = passingScoreField.querySelector('.methodist-form-group:first-child');
            if (gradingForm.value === 'points') {
                if (passingScoreGroup) passingScoreGroup.style.display = 'block';
            } else {
                if (passingScoreGroup) passingScoreGroup.style.display = 'none';
            }
        }
        gradingForm.addEventListener('change', togglePassingScoreField);
        togglePassingScoreField();
    }
    
    const assignmentGradingType = document.querySelector('select[name="grading_type"]');
    const scoreFields = document.getElementById('score-fields');
    if (assignmentGradingType && scoreFields) {
        function toggleScoreFields() {
            if (assignmentGradingType.value === 'points') {
                scoreFields.style.display = 'grid';
            } else {
                scoreFields.style.display = 'none';
            }
        }
        assignmentGradingType.addEventListener('change', toggleScoreFields);
        toggleScoreFields();
    }
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-30px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
    `;
    document.head.appendChild(style);
});

window.confirmDelete = confirmDelete;
window.showNotification = showNotification;
window.validateTestForm = validateTestForm;