document.addEventListener('DOMContentLoaded', function () {
    // Data from json_script tags
    const salesLabels = JSON.parse(document.getElementById('sales-chart-labels').textContent);
    const salesValues = JSON.parse(document.getElementById('sales-chart-values').textContent);
    const topAirlinesData = JSON.parse(document.getElementById('top-airlines-data').textContent);

    // Chart.js defaults
    Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
    Chart.defaults.color = '#858796';

    // Monthly sales bar chart
    const ctxSales = document.getElementById('monthlySalesChart');
    if (ctxSales) {
        new Chart(ctxSales, {
            type: 'bar',
            data: {
                labels: salesLabels,
                datasets: [{
                    label: 'Ventas',
                    data: salesValues,
                    backgroundColor: '#4e73df',
                    hoverBackgroundColor: '#2e59d9',
                    borderColor: '#4e73df',
                    borderRadius: 4,
                }]
            },
            options: {
                maintainAspectRatio: false,
                layout: { padding: { left: 10, right: 25, top: 25, bottom: 0 } },
                scales: {
                    x: { grid: { display: false, drawBorder: false }, ticks: { maxTicksLimit: 6 } },
                    y: {
                        ticks: { maxTicksLimit: 5, padding: 10, callback: function (value) { return '$' + value.toLocaleString(); } },
                        grid: { color: 'rgb(234, 236, 244)', drawBorder: false, borderDash: [2] }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgb(255,255,255)',
                        bodyColor: '#858796',
                        titleColor: '#6e707e',
                        borderColor: '#dddfeb',
                        borderWidth: 1,
                        xPadding: 15,
                        yPadding: 15,
                        displayColors: false,
                        intersect: false,
                        mode: 'index',
                        caretPadding: 10,
                        callbacks: {
                            label: function (tooltipItem) {
                                return tooltipItem.dataset.label + ': $' + tooltipItem.raw.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    // Top airlines doughnut chart
    const ctxAirlines = document.getElementById('airlinesChart');
    if (ctxAirlines) {
        new Chart(ctxAirlines, {
            type: 'doughnut',
            data: {
                labels: topAirlinesData.map(item => item.aerolinea),
                datasets: [{
                    data: topAirlinesData.map(item => item.total),
                    backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796'],
                    hoverBackgroundColor: ['#2e59d9', '#17a673', '#2c9faf', '#dda20a', '#be2617', '#60616f'],
                    hoverBorderColor: 'rgba(234, 236, 244, 1)'
                }]
            },
            options: {
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { display: true, position: 'bottom' },
                    tooltip: {
                        backgroundColor: 'rgb(255,255,255)',
                        bodyColor: '#858796',
                        borderColor: '#dddfeb',
                        borderWidth: 1,
                        callbacks: {
                            label: function (tooltipItem) {
                                return tooltipItem.label + ': $' + tooltipItem.raw.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }
});
