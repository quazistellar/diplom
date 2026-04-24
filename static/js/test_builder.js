class TestBuilder {
    constructor() {
        // данная функция инициализирует свойства класса
        this.currentType = '';
        this.optionCounter = 1;
        this.pairCounter = 1;
        this.isUpdating = false;
        this.isEditMode = false;
        this.init();
    }

    // данная функция выполняет начальную инициализацию компонента
    init() {
        this.answerTypeSelect = this.findAnswerTypeSelect();
        
        if (!this.answerTypeSelect) {
            return;
        }

        this.choicePanel = document.getElementById('choice-options-panel');
        this.matchingPanel = document.getElementById('matching-pairs-panel');
        this.correctTextGroup = document.getElementById('correct-text-group');
        this.optionsContainer = document.getElementById('options-container');
        this.pairsContainer = document.getElementById('pairs-container');
        this.choiceValidation = document.getElementById('choice-validation');
        this.form = document.getElementById('question-form');
        
        // данная функция проверяет наличие существующих опций
        const existingOptions = this.optionsContainer ? 
            this.optionsContainer.querySelectorAll('.option-item').length : 0;
        const existingPairs = this.pairsContainer ? 
            this.pairsContainer.querySelectorAll('.matching-pair-item').length : 0;
        
        this.isEditMode = existingOptions > 0 || existingPairs > 0;
        
        // данная функция добавляет обработчики к существующим элементам
        if (this.isEditMode) {
            this.addHandlersToExistingElements();
        }
        
        // данная функция добавляет обработчик изменения типа вопроса
        this.answerTypeSelect.addEventListener('change', (e) => {
            this.updatePanels(e);
        });
        
        this.updatePanels();
        
        // данная функция настраивает кнопку добавления варианта ответа
        const addOptionBtn = document.getElementById('add-option-btn');
        
        if (addOptionBtn) {
            const newBtn = addOptionBtn.cloneNode(true);
            addOptionBtn.parentNode.replaceChild(newBtn, addOptionBtn);
            newBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.addOption();
            });
        }
        
        // данная функция настраивает кнопку добавления пары соответствия
        const addPairBtn = document.getElementById('add-pair-btn');
        
        if (addPairBtn) {
            const newBtn = addPairBtn.cloneNode(true);
            addPairBtn.parentNode.replaceChild(newBtn, addPairBtn);
            newBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.addPair();
            });
        }
        
        // данная функция настраивает обработчик отправки формы
        if (this.form) {
            if (this.submitHandler) {
                this.form.removeEventListener('submit', this.submitHandler);
            }
            this.submitHandler = (e) => this.handleSubmit(e);
            this.form.addEventListener('submit', this.submitHandler);
        }
        
        this.updateChoiceValidation();
    }
    
    // данная функция добавляет обработчики к существующим элементам (удаление, изменение)
    addHandlersToExistingElements() {
        if (this.optionsContainer) {
            const options = this.optionsContainer.querySelectorAll('.option-item');
            
            options.forEach((option, idx) => {
                // данная функция добавляет обработчик удаления
                const removeBtn = option.querySelector('.remove-option');
                if (removeBtn) {
                    const newRemoveBtn = removeBtn.cloneNode(true);
                    removeBtn.parentNode.replaceChild(newRemoveBtn, removeBtn);
                    newRemoveBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        option.remove();
                        this.updateOptionIndexes();
                        this.updateChoiceValidation();
                    });
                }
                
                // данная функция добавляет обработчик изменения для radio/checkbox
                const radio = option.querySelector('input[type="radio"]');
                const checkbox = option.querySelector('input[type="checkbox"]');
                if (radio) {
                    radio.addEventListener('change', () => {
                        this.updateChoiceValidation();
                    });
                }
                if (checkbox) {
                    checkbox.addEventListener('change', () => {
                        this.updateChoiceValidation();
                    });
                }
            });
        }
        
        if (this.pairsContainer) {
            const pairs = this.pairsContainer.querySelectorAll('.matching-pair-item');
            
            pairs.forEach((pair, idx) => {
                const removeBtn = pair.querySelector('.remove-pair');
                if (removeBtn) {
                    const newRemoveBtn = removeBtn.cloneNode(true);
                    removeBtn.parentNode.replaceChild(newRemoveBtn, removeBtn);
                    newRemoveBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        pair.remove();
                    });
                }
            });
        }
    }
    
    // данная функция находит select для выбора типа ответа
    findAnswerTypeSelect() {
        const selectors = [
            '#answer-type-select',
            '#id_answer_type',
            '[name="answer_type"]',
            'select[id*="answer"]',
            'select[name*="answer"]'
        ];
        
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element && element.tagName === 'SELECT') {
                return element;
            }
        }
        
        const form = document.getElementById('question-form');
        if (form) {
            const selects = form.querySelectorAll('select');
            if (selects.length > 0) {
                return selects[0];
            }
        }
        
        return null;
    }
    
    // данная функция обновляет видимость панелей в зависимости от выбранного типа вопроса
    updatePanels(event = null) {
        
        if (!this.answerTypeSelect) return;
        if (this.isUpdating) return;
        
        this.isUpdating = true;
        const selectedValue = this.answerTypeSelect.value;
        
        if (this.choicePanel) this.choicePanel.style.display = 'none';
        if (this.matchingPanel) this.matchingPanel.style.display = 'none';
        if (this.correctTextGroup) this.correctTextGroup.style.display = 'none';
        
        if (selectedValue === '1') {
            if (this.choicePanel) {
                this.choicePanel.style.display = 'block';
                const radios = this.optionsContainer.querySelectorAll('input[type="radio"]');
                radios.forEach(radio => { radio.name = 'is_correct'; });
            }
        } 
        else if (selectedValue === '2') {
            if (this.choicePanel) {
                this.choicePanel.style.display = 'block';
                const checkboxes = this.optionsContainer.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => { checkbox.name = 'is_correct[]'; });
            }
        }
        else if (selectedValue === '3') {
            if (this.correctTextGroup) this.correctTextGroup.style.display = 'block';
        }
        else if (selectedValue === '4') {
            if (this.matchingPanel) this.matchingPanel.style.display = 'block';
        }
        
        this.isUpdating = false;
        this.updateChoiceValidation();
    }
    
    // данная функция добавляет новый вариант ответа
    addOption() {
        
        if (!this.optionsContainer) return;
        
        const isMultiple = (this.answerTypeSelect?.value === '2');
        const optionId = this.optionCounter++;
        
        const optionDiv = document.createElement('div');
        optionDiv.className = 'option-item';
        
        if (isMultiple) {
            optionDiv.innerHTML = `
                <input type="text" name="option_text[]" placeholder="Введите вариант ответа" required>
                <label class="option-correct-label">
                    <input type="checkbox" name="is_correct[]" value="${optionId}">
                    <span>Правильный</span>
                </label>
                <i class="fas fa-trash remove-option"></i>
            `;
        } else {
            optionDiv.innerHTML = `
                <input type="text" name="option_text[]" placeholder="Введите вариант ответа" required>
                <label class="option-correct-label">
                    <input type="radio" name="is_correct" value="${optionId}">
                    <span>Правильный</span>
                </label>
                <i class="fas fa-trash remove-option"></i>
            `;
        }
        
        const removeBtn = optionDiv.querySelector('.remove-option');
        removeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            optionDiv.remove();
            this.updateOptionIndexes();
            this.updateChoiceValidation();
        });
        
        const input = optionDiv.querySelector('input[type="radio"], input[type="checkbox"]');
        input.addEventListener('change', () => this.updateChoiceValidation());
        
        this.optionsContainer.appendChild(optionDiv);
        this.updateOptionIndexes();
        this.updateChoiceValidation();
    }
    
    // данная функция добавляет новую пару соответствия
    addPair() {
        if (!this.pairsContainer) return;
        const pairId = this.pairCounter++;
        
        const pairDiv = document.createElement('div');
        pairDiv.className = 'matching-pair-item';
        pairDiv.innerHTML = `
            <input type="text" name="left_text[]" placeholder="Левый элемент">
            <i class="fas fa-arrow-right"></i>
            <input type="text" name="right_text[]" placeholder="Правый элемент">
            <i class="fas fa-trash remove-pair"></i>
        `;
        
        const removeBtn = pairDiv.querySelector('.remove-pair');
        removeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            pairDiv.remove();
        });
        
        this.pairsContainer.appendChild(pairDiv);
    }
    
    // данная функция обновляет индексы вариантов ответов
    updateOptionIndexes() {
        if (!this.optionsContainer) return;
        
        const options = this.optionsContainer.querySelectorAll('.option-item');
        const isMultiple = (this.answerTypeSelect?.value === '2');
        
        options.forEach((option, index) => {
            const input = option.querySelector('input[type="radio"], input[type="checkbox"]');
            if (input) {
                input.value = index;
                if (!isMultiple && input.type === 'radio') {
                    input.name = 'is_correct';
                } else if (isMultiple && input.type === 'checkbox') {
                    input.name = 'is_correct[]';
                }
            }
        });
    }
    
    // данная функция обновляет отображение валидации для вариантов ответов
    updateChoiceValidation() {
        if (!this.choiceValidation || !this.optionsContainer) return;
        
        const selectedValue = this.answerTypeSelect?.value;
        
        if (selectedValue !== '1' && selectedValue !== '2') {
            this.choiceValidation.style.display = 'none';
            return;
        }
        
        const options = this.optionsContainer.querySelectorAll('.option-item');
        let hasValidOption = false;
        
        options.forEach(opt => {
            const textInput = opt.querySelector('input[type="text"]');
            if (textInput && textInput.value.trim()) {
                hasValidOption = true;
            }
        });
        
        if (!hasValidOption) {
            this.choiceValidation.style.display = 'block';
            this.choiceValidation.className = 'validation-message validation-error';
            this.choiceValidation.innerHTML = 'Добавьте хотя бы один вариант ответа с текстом';
            return;
        }
        
        const isMultiple = (selectedValue === '2');
        
        if (!isMultiple) {
            const checked = document.querySelectorAll('input[name="is_correct"]:checked');
            if (checked.length === 0) {
                this.choiceValidation.style.display = 'block';
                this.choiceValidation.className = 'validation-message validation-error';
                this.choiceValidation.innerHTML = 'Отметьте правильный вариант ответа';
                return;
            }
            this.choiceValidation.style.display = 'block';
            this.choiceValidation.className = 'validation-message validation-success';
            this.choiceValidation.innerHTML = 'Правильный вариант отмечен';
        } else {
            const checked = document.querySelectorAll('input[name="is_correct[]"]:checked');
            if (checked.length === 0) {
                this.choiceValidation.style.display = 'block';
                this.choiceValidation.className = 'validation-message validation-error';
                this.choiceValidation.innerHTML = 'Отметьте хотя бы один правильный вариант';
                return;
            }
            this.choiceValidation.style.display = 'block';
            this.choiceValidation.className = 'validation-message validation-success';
            this.choiceValidation.innerHTML = 'Выбрано правильных вариантов: ' + checked.length;
        }
    }
    
    // данная функция выполняет валидацию формы перед отправкой
    validateForm() {
        const selectedValue = this.answerTypeSelect.value;
        
        const questionText = document.getElementById('id_question_text');
        if (!questionText.value.trim() || questionText.value.trim().length < 3) {
            alert('Текст вопроса должен содержать минимум 3 символа');
            return false;
        }
        
        const questionScore = document.getElementById('id_question_score');
        if (!questionScore.value || parseInt(questionScore.value) <= 0) {
            alert('Балл за вопрос должен быть положительным числом');
            return false;
        }
        
        const questionOrder = document.getElementById('id_question_order');
        if (!questionOrder.value || parseInt(questionOrder.value) <= 0) {
            alert('Порядковый номер вопроса должен быть положительным числом');
            return false;
        }
        
        if (selectedValue === '3') {
            const correctText = document.getElementById('id_correct_text');
            if (!correctText.value.trim()) {
                alert('Укажите правильный ответ для текстового вопроса');
                return false;
            }
            return true;
        }
        
        if (selectedValue === '4') {
            const leftTexts = document.querySelectorAll('input[name="left_text[]"]');
            let hasValid = false;
            leftTexts.forEach(left => { if (left.value.trim()) hasValid = true; });
            if (!hasValid) {
                alert('Добавьте хотя бы одну пару для сопоставления');
                return false;
            }
            return true;
        }
        
        if (selectedValue === '1' || selectedValue === '2') {
            const optionTexts = document.querySelectorAll('input[name="option_text[]"]');
            let hasValid = false;
            optionTexts.forEach(opt => { if (opt.value.trim()) hasValid = true; });
            
            if (!hasValid) {
                alert('Добавьте хотя бы один вариант ответа с текстом');
                return false;
            }
            
            if (selectedValue === '1') {
                const checked = document.querySelectorAll('input[name="is_correct"]:checked');
                if (checked.length === 0) {
                    alert('Отметьте правильный вариант ответа');
                    return false;
                }
            } else {
                const checked = document.querySelectorAll('input[name="is_correct[]"]:checked');
                if (checked.length === 0) {
                    alert('Отметьте хотя бы один правильный вариант ответа');
                    return false;
                }
            }
            return true;
        }
        
        return true;
    }
    
    // данная функция обрабатывает событие отправки формы
    handleSubmit(e) {
        if (!this.validateForm()) {
            e.preventDefault();
            return false;
        }
        return true;
    }
}

// данная функция инициализирует TestBuilder после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    window.testBuilder = new TestBuilder();
});