/// данная функция получает CSRF токен из cookie
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

/// данная функция экранирует HTML специальные символы
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/// данная функция форматирует дату в локальный формат
function formatDate(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return dateString;
        }
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch(e) {
        return dateString;
    }
}

/// данная функция переключает вкладки и сохраняет активную вкладку
document.addEventListener('DOMContentLoaded', function() {
    const activeTab = localStorage.getItem('activeStudyTab');
    if (activeTab) {
        const tabBtn = document.querySelector(`.study-nav-custom .nav-btn[data-tab="${activeTab}"]`);
        if (tabBtn) {
            document.querySelectorAll('.study-nav-custom .nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.study-tab').forEach(tab => tab.classList.remove('active'));
            tabBtn.classList.add('active');
            const targetTab = document.getElementById(`${activeTab}-tab`);
            if (targetTab) targetTab.classList.add('active');
        }
    }
    
    document.querySelectorAll('.study-nav-custom .nav-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            localStorage.setItem('activeStudyTab', tabName);
            
            document.querySelectorAll('.study-nav-custom .nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.study-tab').forEach(tab => tab.classList.remove('active'));
            
            this.classList.add('active');
            const targetTab = document.getElementById(`${tabName}-tab`);
            if (targetTab) {
                targetTab.classList.add('active');
            }
        });
    });
});

/// данная функция показывает или скрывает комментарии и сохраняет состояние
function toggleComments(element, postId) {
    const commentsDiv = document.getElementById(`comments-${postId}`);
    if (commentsDiv) {
        if (commentsDiv.style.display === 'none' || commentsDiv.style.display === '') {
            commentsDiv.style.display = 'block';
            localStorage.setItem(`comments_open_${postId}`, 'true');
        } else {
            commentsDiv.style.display = 'none';
            localStorage.setItem(`comments_open_${postId}`, 'false');
        }
    }
}

/// данная функция восстанавливает состояние комментариев при загрузке
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.post-card').forEach(card => {
        const postId = card.getAttribute('data-post-id');
        const isOpen = localStorage.getItem(`comments_open_${postId}`);
        const commentsDiv = document.getElementById(`comments-${postId}`);
        if (commentsDiv && isOpen === 'true') {
            commentsDiv.style.display = 'block';
        }
    });
});

/// данная функция показывает форму ответа на комментарий
function showReplyForm(commentId, postId) {
    const form = document.getElementById(`reply-form-${commentId}`);
    if (form) {
        if (form.style.display === 'none' || form.style.display === '') {
            document.querySelectorAll('.reply-form').forEach(f => {
                if (f.id !== `reply-form-${commentId}`) {
                    f.style.display = 'none';
                }
            });
            form.style.display = 'block';
            form.setAttribute('data-post-id', postId);
            const textarea = form.querySelector('.reply-textarea');
            if (textarea) textarea.focus();
        } else {
            form.style.display = 'none';
        }
    }
}

/// данная функция добавляет комментарий в DOM
function addCommentToDOM(postId, comment, isReply = false, parentCommentId = null) {
    const commentsList = document.querySelector(`#comments-${postId} .comments-list`);
    if (!commentsList) return;
    
    const commentHtml = `
        <div class="comment-item" data-comment-id="${comment.id}">
            <div class="comment-avatar">
                <i class="fas fa-user-circle"></i>
            </div>
            <div class="comment-content">
                <div class="comment-author">
                    ${escapeHtml(comment.author_name)}
                    <span class="comment-date">${formatDate(comment.created_at)}</span>
                    ${comment.can_delete ? `<button class="comment-delete" onclick="deleteComment(${comment.id}, ${postId})"><i class="fas fa-trash-alt"></i></button>` : ''}
                </div>
                <div class="comment-text">${escapeHtml(comment.content).replace(/\n/g, '<br>')}</div>
                
                <button class="reply-btn" onclick="showReplyForm(${comment.id}, ${postId})">
                    <i class="fas fa-reply"></i> Ответить
                </button>
                
                <div class="reply-form" id="reply-form-${comment.id}" style="display: none;">
                    <textarea class="reply-textarea" rows="2" placeholder="Написать ответ..."></textarea>
                    <button class="lsn-btn lsn-btn-primary" onclick="submitReply(${comment.id}, ${postId})">
                        <i class="fas fa-paper-plane"></i> Отправить
                    </button>
                </div>
                
                <div class="replies-list" id="replies-${comment.id}"></div>
            </div>
        </div>
    `;
    
    if (isReply && parentCommentId) {
        const repliesContainer = document.getElementById(`replies-${parentCommentId}`);
        if (repliesContainer) {
            repliesContainer.insertAdjacentHTML('beforeend', `
                <div class="reply-item" data-reply-id="${comment.id}">
                    <div class="reply-avatar">
                        <i class="fas fa-user-circle"></i>
                    </div>
                    <div class="reply-content">
                        <div class="reply-author">
                            ${escapeHtml(comment.author_name)}
                            <span class="reply-date">${formatDate(comment.created_at)}</span>
                            ${comment.can_delete ? `<button class="reply-delete" onclick="deleteComment(${comment.id}, ${postId})"><i class="fas fa-trash-alt"></i></button>` : ''}
                        </div>
                        <div class="reply-text">${escapeHtml(comment.content).replace(/\n/g, '<br>')}</div>
                    </div>
                </div>
            `);
        }
    } else {
        const noComments = commentsList.querySelector('.no-comments');
        if (noComments) noComments.remove();
        
        commentsList.insertAdjacentHTML('beforeend', commentHtml);
    }
    
    updateCommentsCount(postId);
}

/// данная функция обновляет счётчик комментариев
function updateCommentsCount(postId) {
    const commentsCount = document.querySelectorAll(`#comments-${postId} .comment-item`).length;
    const repliesCount = document.querySelectorAll(`#comments-${postId} .reply-item`).length;
    const totalCount = commentsCount + repliesCount;
    
    const countSpan = document.querySelector(`.post-card[data-post-id="${postId}"] .reply-count`);
    if (countSpan) {
        const countText = totalCount === 0 ? '0 комментариев' : 
                         (totalCount === 1 ? '1 комментарий' : 
                         (totalCount < 5 ? `${totalCount} комментария` : `${totalCount} комментариев`));
        countSpan.innerHTML = `<i class="fas fa-comment"></i> ${countText}`;
    }
}

/// данная функция отправляет комментарий на сервер
async function submitComment(postId) {
    const textarea = document.getElementById(`new-comment-${postId}`);
    
    if (!textarea) {
        console.error('Textarea not found for postId:', postId);
        alert('Ошибка: поле ввода не найдено.');
        return;
    }
    
    const content = textarea.value.trim();
    
    if (!content) {
        alert('Введите текст комментария');
        return;
    }
    
    const originalText = content;
    textarea.disabled = true;
    textarea.value = 'Отправка...';
    
    try {
        const formData = new FormData();
        formData.append('content', content);
        
        const response = await fetch(`/listener/api/post/${postId}/comment/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success && data.comment) {
            textarea.value = '';
            addCommentToDOM(postId, data.comment);
            const commentsDiv = document.getElementById(`comments-${postId}`);
            if (commentsDiv && commentsDiv.style.display !== 'block') {
                commentsDiv.style.display = 'block';
                localStorage.setItem(`comments_open_${postId}`, 'true');
            }
        } else {
            alert(data.error || 'Ошибка отправки комментария');
            textarea.value = originalText;
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Произошла ошибка: ' + error.message);
        textarea.value = originalText;
    } finally {
        textarea.disabled = false;
    }
}

/// данная функция отправляет ответ на комментарий на сервер
async function submitReply(commentId, postId) {
    const form = document.getElementById(`reply-form-${commentId}`);
    
    if (!form) {
        console.error('Reply form not found for commentId:', commentId);
        alert('Ошибка: форма ответа не найдена.');
        return;
    }
    
    const textarea = form.querySelector('.reply-textarea');
    
    if (!textarea) {
        alert('Ошибка: поле ввода ответа не найдено.');
        return;
    }
    
    const content = textarea.value.trim();
    
    if (!content) {
        alert('Введите текст ответа');
        return;
    }
    
    const originalText = textarea.value;
    textarea.disabled = true;
    textarea.value = 'Отправка...';
    
    try {
        const formData = new FormData();
        formData.append('content', content);
        formData.append('parent_id', commentId);
        
        const response = await fetch(`/listener/api/post/${postId}/comment/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success && data.comment) {
            textarea.value = '';
            form.style.display = 'none';
            addCommentToDOM(postId, data.comment, true, commentId);
        } else {
            alert(data.error || 'Ошибка отправки ответа');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Произошла ошибка: ' + error.message);
    } finally {
        textarea.disabled = false;
        textarea.value = originalText;
    }
}

/// данная функция удаляет комментарий или ответ
async function deleteComment(commentId, postId) {
    if (!confirm('Удалить комментарий?')) return;
    
    try {
        const response = await fetch(`/listener/api/comment/${commentId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const commentElement = document.querySelector(`.comment-item[data-comment-id="${commentId}"], .reply-item[data-reply-id="${commentId}"]`);
            if (commentElement) {
                commentElement.remove();
            } else {
                const commentByClass = document.querySelector(`.comment-item:has(.comment-delete[onclick*="${commentId}"]), .reply-item:has(.reply-delete[onclick*="${commentId}"])`);
                if (commentByClass) commentByClass.remove();
            }
            updateCommentsCount(postId);
        } else {
            alert(data.error || 'Ошибка удаления');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Произошла ошибка: ' + error.message);
    }
}

/// данная функция удаляет пост
async function deletePost(postId) {
    if (!confirm('Удалить объявление?')) return;
    
    try {
        const response = await fetch(`/listener/api/post/${postId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            const postCard = document.querySelector(`.post-card[data-post-id="${postId}"]`);
            if (postCard) {
                postCard.remove();
            }
            const remainingPosts = document.querySelectorAll('.post-card').length;
            if (remainingPosts === 0) {
                const container = document.getElementById('posts-container');
                if (container) {
                    container.innerHTML = `
                        <div class="lsn-empty-state">
                            <i class="fas fa-bullhorn"></i>
                            <h3>Нет объявлений</h3>
                            <p>Объявлений пока нет</p>
                        </div>
                    `;
                }
            }
        } else {
            alert(data.error || 'Ошибка удаления');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Произошла ошибка: ' + error.message);
    }
}

/// данная функция открывает модальное окно редактирования поста
function openEditPostModal(postId) {
    const postCard = document.querySelector(`.post-card[data-post-id="${postId}"]`);
    if (!postCard) return;
    
    const titleElement = postCard.querySelector('.post-title');
    const contentEl = postCard.querySelector('.post-content');
    const pinnedBadge = postCard.querySelector('.pinned-badge');
    
    const title = titleElement ? titleElement.innerText : '';
    let content = '';
    if (contentEl) {
        content = contentEl.innerHTML ? contentEl.innerHTML.replace(/<br>/g, '\n') : '';
        content = content.replace(/<[^>]*>/g, '');
    }
    const isPinned = pinnedBadge !== null;
    
    let postType = 'announcement';
    const postTypeBadge = postCard.querySelector('.post-type-badge');
    if (postTypeBadge) {
        if (postTypeBadge.classList.contains('post-type-question')) postType = 'question';
        else if (postTypeBadge.classList.contains('post-type-reminder')) postType = 'reminder';
    }
    
    const modalHtml = `
    <div id="editPostModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h3><i class="fas fa-edit"></i> Редактировать объявление</h3>
                <button class="modal-close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>Тип объявления</label>
                    <select id="editPostType" class="form-control">
                        <option value="announcement" ${postType === 'announcement' ? 'selected' : ''}>📢 Объявление</option>
                        <option value="question" ${postType === 'question' ? 'selected' : ''}>❓ Вопрос</option>
                        <option value="reminder" ${postType === 'reminder' ? 'selected' : ''}>⏰ Напоминание</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Заголовок</label>
                    <input type="text" id="editPostTitle" class="form-control" value="${escapeHtml(title)}">
                </div>
                <div class="form-group">
                    <label>Содержание</label>
                    <textarea id="editPostContent" rows="5" class="form-control">${escapeHtml(content)}</textarea>
                </div>
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="editPostPinned" ${isPinned ? 'checked' : ''}> Закрепить объявление
                    </label>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-cancel" onclick="closeEditModal()">Отмена</button>
                <button class="btn-submit" onclick="updatePost(${postId})">Сохранить</button>
            </div>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/// данная функция закрывает модальное окно редактирования поста
function closeEditModal() {
    const modal = document.getElementById('editPostModal');
    if (modal) modal.remove();
}

/// данная функция обновляет существующий пост
async function updatePost(postId) {
    const title = document.getElementById('editPostTitle')?.value.trim();
    const content = document.getElementById('editPostContent')?.value.trim();
    const postType = document.getElementById('editPostType')?.value;
    const isPinned = document.getElementById('editPostPinned')?.checked;
    
    if (!title || title.length < 3) {
        alert('Заголовок должен содержать минимум 3 символа');
        return;
    }
    if (!content || content.length < 10) {
        alert('Содержание должно содержать минимум 10 символов');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('content', content);
        formData.append('post_type', postType);
        formData.append('is_pinned', isPinned);
        
        const response = await fetch(`/listener/api/post/${postId}/edit/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeEditModal();
            const postCard = document.querySelector(`.post-card[data-post-id="${postId}"]`);
            if (postCard) {
                const titleEl = postCard.querySelector('.post-title');
                const contentEl = postCard.querySelector('.post-content');
                const typeBadge = postCard.querySelector('.post-type-badge');
                const pinnedBadge = postCard.querySelector('.pinned-badge');
                
                if (titleEl) titleEl.textContent = title;
                if (contentEl) contentEl.innerHTML = content.replace(/\n/g, '<br>');
                
                if (typeBadge) {
                    let icon = 'fa-bullhorn';
                    let typeText = 'Объявление';
                    if (postType === 'question') {
                        icon = 'fa-question-circle';
                        typeText = 'Вопрос';
                    } else if (postType === 'reminder') {
                        icon = 'fa-bell';
                        typeText = 'Напоминание';
                    }
                    typeBadge.innerHTML = `<i class="fas ${icon}"></i> ${typeText}`;
                    typeBadge.className = `post-type-badge post-type-${postType}`;
                }
                
                if (isPinned) {
                    if (!pinnedBadge) {
                        const headerDiv = postCard.querySelector('.post-header');
                        const typeDiv = headerDiv?.querySelector('div:first-child');
                        if (typeDiv) {
                            typeDiv.insertAdjacentHTML('beforeend', '<span class="pinned-badge"><i class="fas fa-thumbtack"></i> Закреплено</span>');
                        }
                    }
                } else {
                    if (pinnedBadge) pinnedBadge.remove();
                }
            }
        } else {
            alert(data.error || 'Ошибка обновления');
        }
    } catch (error) {
        alert('Произошла ошибка: ' + error.message);
    }
}