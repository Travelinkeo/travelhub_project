import pytest


@pytest.mark.django_db

def test_create_and_list_new_components(api_client_staff, venta_base):
    venta = venta_base
    client = api_client_staff

    # Crear alquiler auto
    resp_auto = client.post('/core/api/alquileres-autos/', {
        'venta': venta.id_venta,
        'categoria_auto': 'SUV',
        'compania_rentadora': 'Hertz',
        'incluye_seguro': True
    }, format='json')
    assert resp_auto.status_code in (200,201), resp_auto.content

    # Crear evento
    resp_evento = client.post('/core/api/eventos-servicios/', {
        'venta': venta.id_venta,
        'nombre_evento': 'Concierto',
    }, format='json')
    assert resp_evento.status_code in (200,201), resp_evento.content

    # Crear circuito + dia
    resp_circuito = client.post('/core/api/circuitos-turisticos/', {
        'venta': venta.id_venta,
        'nombre_circuito': 'Europa Express'
    }, format='json')
    assert resp_circuito.status_code in (200,201), resp_circuito.content
    circuito_id = resp_circuito.json()['id_circuito']

    resp_dia = client.post('/core/api/circuitos-dias/', {
        'circuito': circuito_id,
        'dia_numero': 1,
        'titulo': 'Llegada'
    }, format='json')
    assert resp_dia.status_code in (200,201), resp_dia.content

    # Crear paquete aéreo
    resp_paquete = client.post('/core/api/paquetes-aereos/', {
        'venta': venta.id_venta,
        'nombre_paquete': 'Aereo + Hotel'
    }, format='json')
    assert resp_paquete.status_code in (200,201), resp_paquete.content

    # Crear servicio adicional
    resp_servicio = client.post('/core/api/servicios-adicionales/', {
        'venta': venta.id_venta,
        'tipo_servicio': 'SEG'
    }, format='json')
    assert resp_servicio.status_code in (200,201), resp_servicio.content

    # Listar y validar conteos
    list_auto = client.get('/core/api/alquileres-autos/')
    list_evento = client.get('/core/api/eventos-servicios/')
    list_circuitos = client.get('/core/api/circuitos-turisticos/')
    list_paquetes = client.get('/core/api/paquetes-aereos/')
    list_servicios = client.get('/core/api/servicios-adicionales/')

    assert list_auto.status_code == 200
    assert list_evento.status_code == 200
    assert list_circuitos.status_code == 200
    assert list_paquetes.status_code == 200
    assert list_servicios.status_code == 200

    assert list_auto.json()['count'] >= 1
    assert list_evento.json()['count'] >= 1
    assert list_circuitos.json()['count'] >= 1
    assert list_paquetes.json()['count'] >= 1
    assert list_servicios.json()['count'] >= 1

    # Recuperar venta y verificar presencia de arrays embebidos
    venta_resp = client.get(f'/core/api/ventas/{venta.id_venta}/')
    assert venta_resp.status_code == 200
    data = venta_resp.json()
    for key in ['alquileres_autos','eventos_servicios','circuitos_turisticos','paquetes_aereos','servicios_adicionales']:
        assert key in data
        assert isinstance(data[key], list)
