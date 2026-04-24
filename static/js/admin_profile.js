/*  
    функции для профиля администратора
*/

function switchTab(button, tabName) {
    var allButtons = document.querySelectorAll('.profile-nav-btn');
    for (var i = 0; i < allButtons.length; i++) {
        allButtons[i].classList.remove('active');
    }
    
    if (button) {
        button.classList.add('active');
    }
    
    var allTabs = document.querySelectorAll('.profile-tab');
    for (var i = 0; i < allTabs.length; i++) {
        allTabs[i].classList.remove('active');
    }
    
    var selectedTab = document.getElementById('tab-' + tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    localStorage.setItem('activeAdminTab', tabName);
}

function restoreActiveTab() {
    var passwordTab = document.getElementById('tab-password');
    if (passwordTab && passwordTab.querySelector('.profile-form-error')) {
        var passwordButton = document.querySelector('.profile-nav-btn[data-tab="password"]');
        if (passwordButton) {
            switchTab(passwordButton, 'password');
            return;
        }
    }
    
    var infoTab = document.getElementById('tab-info');
    if (infoTab && infoTab.querySelector('.profile-form-error')) {
        var infoButton = document.querySelector('.profile-nav-btn[data-tab="info"]');
        if (infoButton) {
            switchTab(infoButton, 'info');
            return;
        }
    }
    
    var savedTab = localStorage.getItem('activeAdminTab');
    if (savedTab && (savedTab === 'info' || savedTab === 'password' || savedTab === 'analytics')) {
        var button = document.querySelector('.profile-nav-btn[data-tab="' + savedTab + '"]');
        if (button) {
            switchTab(button, savedTab);
        }
    }
}

function createActivityChart(activityLabels, activityData) {
    var activityCtx = document.getElementById('activityChart');
    if (activityCtx) {
        new Chart(activityCtx, {
            type: 'line',
            data: {
                labels: activityLabels,
                datasets: [{
                    label: 'Записей на курсы',
                    data: activityData,
                    borderColor: '#8A4FFF',
                    backgroundColor: 'rgba(138, 79, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#E8EAFF'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#B8BFFF'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#B8BFFF'
                        }
                    }
                }
            }
        });
    }
}

function createLoginChart(loginLabels, loginData) {
    var loginCtx = document.getElementById('loginChart');
    if (loginCtx) {
        new Chart(loginCtx, {
            type: 'bar',
            data: {
                labels: loginLabels,
                datasets: [{
                    label: 'Входы в систему',
                    data: loginData,
                    backgroundColor: 'rgba(46, 204, 113, 0.6)',
                    borderColor: '#2ecc71',
                    borderWidth: 2,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#E8EAFF'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: '#B8BFFF'
                        },
                        title: {
                            display: true,
                            text: 'Количество входов',
                            color: '#B8BFFF'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#B8BFFF'
                        },
                        title: {
                            display: true,
                            text: 'Дата',
                            color: '#B8BFFF'
                        }
                    }
                }
            }
        });
    }
}

function initCharts(activityLabels, activityData, loginLabels, loginData) {
    createActivityChart(activityLabels, activityData);
    createLoginChart(loginLabels, loginData);
}

function autoHideMessages() {
    var messages = document.querySelectorAll('.profile-message');
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
}

document.addEventListener('DOMContentLoaded', function() {
    restoreActiveTab();
    autoHideMessages();

    var activityLabelsElem = document.getElementById('activity-labels-data');
    var activityDataElem = document.getElementById('activity-data-data');
    var loginLabelsElem = document.getElementById('login-labels-data');
    var loginDataElem = document.getElementById('login-data-data');
    
    if (activityLabelsElem && activityDataElem && loginLabelsElem && loginDataElem) {
        var activityLabels = JSON.parse(activityLabelsElem.textContent);
        var activityData = JSON.parse(activityDataElem.textContent);
        var loginLabels = JSON.parse(loginLabelsElem.textContent);
        var loginData = JSON.parse(loginDataElem.textContent);
        
        initCharts(activityLabels, activityData, loginLabels, loginData);
    }
});