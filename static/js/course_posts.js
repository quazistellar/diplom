let currentCourseId = null;
let canCreatePosts = false;
let csrfToken = null;

/// данная функция получает CSRF токен из cookie (резервный вариант)
function getCSRFToken() {
    if (csrfToken) return csrfToken;
    
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

/// данная функция инициализирует модуль с courseId и CSRF токеном
function initCoursePosts(courseId, csrf) {
    currentCourseId = courseId;
    csrfToken = csrf;
}

/// данная функция загружает посты с сервера
function loadPosts() {
    const container = document.getElementById('posts-container');
    if (!container) return;
    
    container.innerHTML = '<div style="text-align: center; padding: 50px;"><i class="fas fa-spinner fa-pulse" style="font-size: 32px;"></i><p>Загрузка объявлений...</p></div>';
    
    fetch(`/listener/api/course/${currentCourseId}/posts/`)
        .then(response => response.json())
        .then(data => {
            canCreatePosts = data.can_create;
            renderPosts(data.posts);
        })
        .catch(error => {
            console.error('Error:', error);
            container.innerHTML = '<div style="text-align: center; padding: 50px; color: #e74c3c;"><i class="fas fa-exclamation-circle"></i><p>Ошибка загрузки объявлений</p></div>';
        });
}

/// данная функция отображает посты на странице
function renderPosts(posts) {
    const container = document.getElementById('posts-container');
    
    if (!posts || posts.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; background: var(--surface); border-radius: 20px;">
                <i class="fas fa-bullhorn" style="font-size: 48px; color: var(--text-soft); margin-bottom: 20px;"></i>
                <h3>Нет объявлений</h3>
                <p>Преподаватель ещё не создал ни одного объявления</p>
                ${canCreatePosts ? '<button class="lsn-btn lsn-btn-primary" onclick="openCreatePostModal()"><i class="fas fa-plus"></i> Создать объявление</button>' : ''}
            </div>
        `;
        return;
    }
    
    let html = '';
    if (canCreatePosts) {
        html += `<div style="margin-bottom: 20px; text-align: right;">
            <button class="lsn-btn lsn-btn-primary" onclick="openCreatePostModal()">
                <i class="fas fa-plus"></i> Создать объявление
            </button>
        </div>`;
    }
    
    posts.forEach(post => {
        html += `
        <div class="post-card ${post.is_pinned ? 'pinned' : ''}" data-post-id="${post.id}">
            <div class="post-header">
                <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                    <span class="post-type-badge post-type-${post.post_type}">
                        <i class="fas ${post.post_type === 'announcement' ? 'fa-bullhorn' : (post.post_type === 'question' ? 'fa-question-circle' : 'fa-bell')}"></i>
                        ${post.post_type_display}
                    </span>
                    ${post.is_pinned ? '<span class="pinned-badge"><i class="fas fa-thumbtack"></i> Закреплено</span>' : ''}
                </div>
                ${post.can_edit ? `
                <div class="post-actions">
                    <button class="post-edit-btn" onclick="openEditPostModal(${post.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="post-delete-btn" onclick="deletePost(${post.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                ` : ''}
            </div>
            <div class="post-body">
                <h3 class="post-title">${escapeHtml(post.title)}</h3>
                <div class="post-content">${escapeHtml(post.content).replace(/\n/g, '<br>')}</div>
                <div class="post-meta">
                    <span><i class="fas fa-user"></i> ${escapeHtml(post.author_name)}</span>
                    <span><i class="fas fa-calendar"></i> ${post.created_at}</span>
                    <span><i class="fas fa-comments"></i> ${post.comments.length} комментариев</span>
                </div>
                
                <div class="comments-section">
                    <div id="comments-${post.id}">
                        ${renderComments(post.comments)}
                    </div>
                    <div class="add-comment-form">
                        <textarea id="comment-${post.id}" rows="2" placeholder="Написать комментарий..."></textarea>
                        <button class="lsn-btn lsn-btn-primary" onclick="addComment(${post.id})">
                            <i class="fas fa-paper-plane"></i> Отправить
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;
    });
    
    container.innerHTML = html;
}

/// данная функция отображает комментарии к посту
function renderComments(comments) {
    if (!comments.length) {
        return '<p class="no-comments">Нет комментариев</p>';
    }
    
    let html = '';
    comments.forEach(comment => {
        html += `
        <div class="comment-item" data-comment-id="${comment.id}">
            <div class="comment-header">
                <div>
                    <span class="comment-author">${escapeHtml(comment.author_name)}</span>
                    <span class="comment-date">${comment.created_at}</span>
                </div>
                ${comment.can_delete ? `<span class="comment-delete" onclick="deleteComment(${comment.id})"><i class="fas fa-trash-alt"></i> Удалить</span>` : ''}
            </div>
            <p class="comment-content">${escapeHtml(comment.content)}</p>
        </div>
        `;
    });
    return html;
}

/// данная функция открывает модальное окно создания поста
function openCreatePostModal() {
    const modalHtml = `
    <div id="postModal" class="modal-overlay">
        <div class="modal-container">
            <div class="modal-header">
                <h3><i class="fas fa-bullhorn"></i> Создать объявление</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>Тип объявления</label>
                    <select id="modalPostType" class="form-control">
                        <option value="announcement">Объявление</option>
                        <option value="question">Вопрос</option>
                        <option value="reminder">Напоминание</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Заголовок</label>
                    <input type="text" id="modalPostTitle" class="form-control" placeholder="Введите заголовок">
                </div>
                <div class="form-group">
                    <label>Содержание</label>
                    <textarea id="modalPostContent" rows="5" class="form-control" placeholder="Введите текст объявления..."></textarea>
                </div>
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="modalPostPinned"> Закрепить объявление
                    </label>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-cancel" onclick="closeModal()">Отмена</button>
                <button class="btn-submit" onclick="createPost()">Создать</button>
            </div>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/// данная функция открывает модальное окно редактирования поста
function openEditPostModal(postId) {
    fetch(`/listener/api/course/${currentCourseId}/posts/`)
        .then(response => response.json())
        .then(data => {
            const post = data.posts.find(p => p.id === postId);
            if (!post) return;
            
            const modalHtml = `
            <div id="postModal" class="modal-overlay">
                <div class="modal-container">
                    <div class="modal-header">
                        <h3><i class="fas fa-edit"></i> Редактировать</h3>
                        <button class="modal-close" onclick="closeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label>Тип объявления</label>
                            <select id="modalPostType" class="form-control">
                                <option value="announcement" ${post.post_type === 'announcement' ? 'selected' : ''}>📢 Объявление</option>
                                <option value="question" ${post.post_type === 'question' ? 'selected' : ''}>❓ Вопрос</option>
                                <option value="reminder" ${post.post_type === 'reminder' ? 'selected' : ''}>⏰ Напоминание</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Заголовок</label>
                            <input type="text" id="modalPostTitle" class="form-control" value="${escapeHtml(post.title)}">
                        </div>
                        <div class="form-group">
                            <label>Содержание</label>
                            <textarea id="modalPostContent" rows="5" class="form-control">${escapeHtml(post.content)}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="checkbox-label">
                                <input type="checkbox" id="modalPostPinned" ${post.is_pinned ? 'checked' : ''}> Закрепить объявление
                            </label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn-cancel" onclick="closeModal()">Отмена</button>
                        <button class="btn-submit" onclick="updatePost(${postId})">Сохранить</button>
                    </div>
                </div>
            </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        });
}

/// данная функция закрывает модальное окно
function closeModal() {
    const modal = document.getElementById('postModal');
    if (modal) modal.remove();
}

/// данная функция создаёт новый пост
function createPost() {
    const title = document.getElementById('modalPostTitle')?.value.trim();
    const content = document.getElementById('modalPostContent')?.value.trim();
    const postType = document.getElementById('modalPostType')?.value;
    const isPinned = document.getElementById('modalPostPinned')?.checked;
    
    if (!title || title.length < 3) {
        alert('Заголовок должен содержать минимум 3 символа');
        return;
    }
    if (!content || content.length < 10) {
        alert('Содержание должно содержать минимум 10 символов');
        return;
    }
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    formData.append('post_type', postType);
    formData.append('is_pinned', isPinned);
    
    fetch(`/listener/api/course/${currentCourseId}/post/create/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeModal();
            loadPosts();
        } else {
            alert(data.error || 'Ошибка создания');
        }
    });
}

/// данная функция обновляет существующий пост
function updatePost(postId) {
    const title = document.getElementById('modalPostTitle')?.value.trim();
    const content = document.getElementById('modalPostContent')?.value.trim();
    const postType = document.getElementById('modalPostType')?.value;
    const isPinned = document.getElementById('modalPostPinned')?.checked;
    
    if (!title || title.length < 3) {
        alert('Заголовок должен содержать минимум 3 символа');
        return;
    }
    if (!content || content.length < 10) {
        alert('Содержание должно содержать минимум 10 символов');
        return;
    }
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    formData.append('post_type', postType);
    formData.append('is_pinned', isPinned);
    
    fetch(`/listener/api/post/${postId}/edit/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeModal();
            loadPosts();
        } else {
            alert(data.error || 'Ошибка обновления');
        }
    });
}

/// данная функция удаляет пост
function deletePost(postId) {
    if (!confirm('Удалить это объявление?')) return;
    
    fetch(`/listener/api/post/${postId}/delete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadPosts();
        } else {
            alert(data.error || 'Ошибка удаления');
        }
    });
}

/// данная функция добавляет комментарий к посту
function addComment(postId) {
    const textarea = document.getElementById(`comment-${postId}`);
    const content = textarea?.value.trim();
    
    if (!content || content.length < 2) {
        alert('Комментарий слишком короткий');
        return;
    }
    
    const formData = new FormData();
    formData.append('content', content);
    
    fetch(`/listener/api/post/${postId}/comment/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.comment) {
            textarea.value = '';
            loadPosts();
        } else {
            alert(data.error || 'Ошибка добавления комментария');
        }
    });
}

/// данная функция удаляет комментарий
function deleteComment(commentId) {
    if (!confirm('Удалить комментарий?')) return;
    
    fetch(`/listener/api/comment/${commentId}/delete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadPosts();
        } else {
            alert(data.error || 'Ошибка удаления');
        }
    });
}

/// данная функция экранирует HTML специальные символы
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}