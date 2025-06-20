document.addEventListener('DOMContentLoaded', function() {
    // Función para mostrar la alerta de saldo negativo
    function checkNegativeBalance() {
        const saldoTotal = parseFloat(JSON.parse(document.getElementById('saldo-total-data').textContent));
        const alertElement = document.getElementById('negativeBalanceAlert');
        if (saldoTotal < 0) {
            alertElement.style.display = 'block';
            setTimeout(() => {
                alertElement.style.display = 'none';
            }, 5000);
        }
    }

    // Función para crear gráfico de pastel (no se usa, pero la dejo por si la necesitas)
    function createPieChart(canvasId, data, colors) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return;
        try {
            var chartData = JSON.parse(data);
            if (!chartData || !Array.isArray(chartData) || chartData.length === 0) return;
            var labels = chartData.map(item => item.categoria);
            var values = chartData.map(item => item.monto);
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: { position: 'right' },
                    tooltips: {
                        callbacks: {
                            label: function(tooltipItem, data) {
                                var value = data.datasets[0].data[tooltipItem.index];
                                var label = data.labels[tooltipItem.index];
                                return `${label}: $${value.toLocaleString('es-CL')}`;
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating pie chart:', e);
        }
    }

    // Función para crear gráfico donut con total al centro
    function createDonutChart(canvasId, data, colors, total) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return;
        var chartData = JSON.parse(data);
        var labels = chartData.map(item => item.categoria);
        var values = chartData.map(item => item.monto);

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0
                }]
            },
            options: {
                cutoutPercentage: 75,
                responsive: true,
                maintainAspectRatio: false,
                legend: { display: false },
                tooltips: { enabled: false }
            },
            plugins: [{
                afterDraw: function(chart) {
                    var ctx = chart.ctx;
                    ctx.save();
                    var width = chart.width, height = chart.height;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    // Texto superior
                    ctx.font = 'bold 16px sans-serif';
                    ctx.fillStyle = '#888';
                    ctx.fillText('Gastos totales', width / 2, height / 2 - 10);
                    // Texto monto
                    ctx.font = 'bold 22px sans-serif';
                    ctx.fillStyle = '#222';
                    ctx.fillText('$' + total.toLocaleString('es-CL'), width / 2, height / 2 + 18);
                    ctx.restore();
                }
            }]
        });
    }

    // Crear gráfico de barras
    var ctxBar = document.getElementById('gastosMesChart');
    if (ctxBar) {
        // Estos datos deben estar disponibles como variables globales o puedes pasarlos desde Django como JSON en el template
        var mesesGastos = window.mesesGastos || [];
        var gastosPorMes = window.gastosPorMes || [];
        new Chart(ctxBar, {
            type: 'line',
            data: {
                labels: mesesGastos,
                datasets: [{
                    label: 'Gastos por Mes',
                    data: gastosPorMes,
                    backgroundColor: 'rgba(255, 99, 132, 0.5)', // Rojo claro para el área
                    borderColor: 'rgb(255, 99, 132)', // Rojo más oscuro para la línea
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: 'rgb(255, 99, 132)' // Color de los puntos
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { display: true },
                scales: {
                    xAxes: [{
                        gridLines: { display: false },
                        ticks: { maxRotation: 0, fontSize: 12 }
                    }],
                    yAxes: [{
                        ticks: {
                            beginAtZero: true,
                            callback: function(value) {
                                return '$' + value.toLocaleString('es-CL');
                            },
                            fontSize: 11
                        },
                        gridLines: { color: "rgba(0, 0, 0, 0.05)" }
                    }]
                },
                tooltips: {
                    callbacks: {
                        label: function(tooltipItem, data) {
                            return '$' + tooltipItem.yLabel.toLocaleString('es-CL');
                        }
                    }
                }
            }
        });
    }

    // Colores para el gráfico de gastos por categoría
    var gastosColors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
        '#FF9F40', '#8DD17E', '#D7263D', '#6C3483', '#F7B731'
    ];

    // Gráfico donut de gastos por categoría
    var gastosData = document.getElementById('gastos-categorias-data');
    if (gastosData) {
        var chartData = JSON.parse(gastosData.textContent);
        var totalGastos = chartData.reduce((acc, item) => acc + parseFloat(item.monto), 0);
        createDonutChart('balanceChart', gastosData.textContent, gastosColors, totalGastos);

        // Leyenda personalizada
        var legendContainer = document.getElementById('donut-legend');
        if (legendContainer) {
            legendContainer.innerHTML = '';
            chartData.forEach(function(item, idx) {
                var color = gastosColors[idx % gastosColors.length];
                var legendItem = document.createElement('div');
                legendItem.className = 'd-flex align-items-center me-3 mb-2';
                legendItem.innerHTML = `
                    <span style="display:inline-block;width:16px;height:16px;background:${color};border-radius:3px;margin-right:8px;"></span>
                    <span style="font-size: 0.97em;">${item.categoria}</span>
                `;
                legendContainer.appendChild(legendItem);
            });
        }
    }

    // Selector de periodo
    const mesAnioSelect = document.getElementById('mes_anio');
    if (mesAnioSelect) {
        mesAnioSelect.addEventListener('change', function() {
            const value = this.value;
            const url = new URL(window.location.href);
            url.searchParams.set('mes_anio', value);
            window.location.href = url.toString();
        });
    }

    // Lógica para el botón de "Generar Recomendaciones"
    const btnGenerarRecomendaciones = document.getElementById('btn-generar-recomendaciones');
    const recomendacionesContainer = document.getElementById('recomendaciones-container');
    const recomendacionesTexto = document.getElementById('recomendaciones-texto');

    if (btnGenerarRecomendaciones && recomendacionesContainer && recomendacionesTexto) {
        btnGenerarRecomendaciones.addEventListener('click', function () {
            // Mostrar el contenedor de recomendaciones y el mensaje de carga
            recomendacionesContainer.style.display = 'block';
            recomendacionesTexto.innerHTML = `
                <div class="d-flex flex-column align-items-center">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="text-muted">Estamos generando tus recomendaciones, por favor espera...</p>
                </div>
            `;

            // Realizar la solicitud AJAX para obtener las recomendaciones
            fetch('/generar-recomendaciones/')
                .then(response => response.json())
                .then(data => {
                    if (data.recomendaciones) {
                        // Usar la librería marked para renderizar Markdown
                        recomendacionesTexto.innerHTML = marked.parse(data.recomendaciones);
                    } else {
                        recomendacionesTexto.textContent = "No se pudieron generar recomendaciones.";
                    }
                })
                .catch(error => {
                    recomendacionesTexto.textContent = "Error al obtener recomendaciones: " + error;
                });
        });
    }
});