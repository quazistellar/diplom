/* 
    файл для отображения статистики методиста
*/

document.addEventListener('DOMContentLoaded', function() {
    if (typeof courseNames === 'undefined' ||
        typeof totalData === 'undefined' ||
        typeof completedData === 'undefined' ||
        typeof popularNames === 'undefined' ||
        typeof popularRatings === 'undefined' ||
        typeof popularStudents === 'undefined') {
        console.warn('Данные для графиков не найдены');
        return;
    }

    const studentsCtx = document.getElementById('studentsChart');
    if (studentsCtx && courseNames.length > 0) {
        new Chart(studentsCtx, {
            type: 'bar',
            data: {
                labels: courseNames,
                datasets: [
                    {
                        label: 'Всего записей',
                        data: totalData,
                        backgroundColor: 'rgba(138, 79, 255, 0.8)',
                        borderColor: 'rgba(138, 79, 255, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Завершено',
                        data: completedData,
                        backgroundColor: 'rgba(46, 204, 113, 0.8)',
                        borderColor: 'rgba(46, 204, 113, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text') || '#E8EAFF'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF'
                        },
                        grid: {
                            color: 'rgba(138, 79, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    const ratingsCtx = document.getElementById('ratingsChart');
    if (ratingsCtx && popularNames.length > 0) {
        new Chart(ratingsCtx, {
            type: 'bar',
            data: {
                labels: popularNames,
                datasets: [
                    {
                        label: 'Средний рейтинг',
                        data: popularRatings,
                        backgroundColor: 'rgba(241, 196, 15, 0.8)',
                        borderColor: 'rgba(241, 196, 15, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Количество слушателей',
                        data: popularStudents,
                        backgroundColor: 'rgba(255, 79, 216, 0.8)',
                        borderColor: 'rgba(255, 79, 216, 1)',
                        borderWidth: 1,
                        type: 'line',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text') || '#E8EAFF'
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Рейтинг',
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF'
                        },
                        min: 0,
                        max: 5,
                        ticks: {
                            stepSize: 1,
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF'
                        },
                        grid: {
                            color: 'rgba(138, 79, 255, 0.1)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Количество слушателей',
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF'
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    x: {
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-soft') || '#B8BFFF',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    const startDateInput = document.querySelector('input[name="start_date"]');
    const endDateInput = document.querySelector('input[name="end_date"]');
    const today = new Date().toISOString().split('T')[0];

    if (startDateInput && endDateInput) {
        startDateInput.max = today;
        endDateInput.max = today;

        startDateInput.addEventListener('change', function() {
            if (this.value > endDateInput.value) {
                endDateInput.value = this.value;
            }
        });

        endDateInput.addEventListener('change', function() {
            if (this.value < startDateInput.value) {
                startDateInput.value = this.value;
            }
        });
    }
});