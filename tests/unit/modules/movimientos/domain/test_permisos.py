from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.entities import EstadoMovimiento as E
from modules.movimientos.domain.entities import TipoMovimiento
from modules.movimientos.domain.permisos import (
    AccionMovimiento as A,
)
from modules.movimientos.domain.permisos import (
    acciones_de_item,
    acciones_permitidas,
    puede_aceptar_acta,
    puede_ver,
    tiene_el_activo,
)

ADMIN = "administrador_general"
EMPLEADO = "empleado"


def _acciones(fabrica, estado_item, actor_id, rol, *, responsable_actual="u1", estado=E.SOLICITADO, tipo=TipoMovimiento.PRESTAMO):
    item = fabrica.item(estado=estado_item)
    movimiento = fabrica.movimiento(tipo=tipo, items=[item], estado=estado, usuario_destino_id="u2")

    return acciones_de_item(movimiento, item, actor_id, rol, responsable_actual)


# --- activo que espera al responsable ---


def test_el_responsable_aprueba_o_rechaza_su_activo(fabrica):
    assert _acciones(fabrica, I.PENDIENTE_RESPONSABLE, "u1", EMPLEADO) == [A.APROBAR, A.RECHAZAR]


def test_otro_usuario_no_decide_el_activo_de_un_responsable(fabrica):
    assert _acciones(fabrica, I.PENDIENTE_RESPONSABLE, "u9", EMPLEADO) == []


def test_el_administrador_solo_decide_ese_paso_si_es_el_responsable(fabrica):
    assert _acciones(fabrica, I.PENDIENTE_RESPONSABLE, "u7", ADMIN) == []
    assert _acciones(fabrica, I.PENDIENTE_RESPONSABLE, "u1", ADMIN) == [A.APROBAR, A.RECHAZAR]


# --- activo que espera a administracion ---


def test_administracion_confirma_la_salida_o_rechaza(fabrica):
    assert _acciones(fabrica, I.PENDIENTE_ADMIN, "u7", ADMIN, estado=E.APROBADO_RESPONSABLE) == [
        A.CONFIRMAR_SALIDA,
        A.RECHAZAR,
    ]


def test_quien_no_es_administrador_no_confirma_la_salida(fabrica):
    assert _acciones(fabrica, I.PENDIENTE_ADMIN, "u1", EMPLEADO, estado=E.APROBADO_RESPONSABLE) == []


def test_la_baja_se_aprueba_y_luego_se_ejecuta(fabrica):
    baja = dict(tipo=TipoMovimiento.BAJA)

    assert _acciones(fabrica, I.PENDIENTE_ADMIN, "u7", ADMIN, estado=E.SOLICITADO, **baja) == [A.APROBAR, A.RECHAZAR]
    assert _acciones(fabrica, I.PENDIENTE_ADMIN, "u7", ADMIN, estado=E.APROBADO, **baja) == [A.EJECUTAR_BAJA]
    assert _acciones(fabrica, I.PENDIENTE_ADMIN, "u1", EMPLEADO, estado=E.SOLICITADO, **baja) == []


# --- activo que esta fuera ---


def test_quien_tiene_el_activo_pide_devolverlo(fabrica):
    assert _acciones(fabrica, I.EN_CURSO, "u2", EMPLEADO, responsable_actual="u2", estado=E.EN_CURSO) == [
        A.SOLICITAR_DEVOLUCION
    ]


def test_el_responsable_original_no_pide_la_devolucion_de_lo_que_tiene_otro(fabrica):
    assert _acciones(fabrica, I.EN_CURSO, "u1", EMPLEADO, responsable_actual="u2", estado=E.EN_CURSO) == []


def test_administracion_recibe_lo_que_esta_fuera_aunque_no_se_haya_pedido(fabrica):
    assert A.CONFIRMAR_DEVOLUCION in _acciones(fabrica, I.EN_CURSO, "u7", ADMIN, responsable_actual="u2", estado=E.EN_CURSO)


def test_con_la_devolucion_solicitada_solo_administracion_puede_recibir(fabrica):
    assert _acciones(fabrica, I.DEVOLUCION_SOLICITADA, "u2", EMPLEADO, responsable_actual="u2", estado=E.EN_CURSO) == []
    assert _acciones(fabrica, I.DEVOLUCION_SOLICITADA, "u7", ADMIN, estado=E.EN_CURSO) == [A.CONFIRMAR_DEVOLUCION]


def test_un_activo_terminado_no_admite_acciones(fabrica):
    for terminal in (I.RECHAZADO, I.DEVUELTO, I.EJECUTADO):
        assert _acciones(fabrica, terminal, "u7", ADMIN, estado=E.DEVUELTO) == []


# --- el movimiento completo ---


def test_las_acciones_del_movimiento_son_la_union_de_las_de_cada_activo(fabrica):
    movimiento = fabrica.movimiento(
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1", estado=I.PENDIENTE_RESPONSABLE),
            fabrica.item(activo_id="a2", responsable_original_id="u3", estado=I.PENDIENTE_RESPONSABLE),
        ]
    )
    responsables = {"a1": "u1", "a2": "u3"}

    assert acciones_permitidas(movimiento, "u1", EMPLEADO, responsables) == [A.APROBAR, A.RECHAZAR]
    assert acciones_permitidas(movimiento, "u3", EMPLEADO, responsables) == [A.APROBAR, A.RECHAZAR]
    assert acciones_permitidas(movimiento, "u9", EMPLEADO, responsables) == []


def test_cada_responsable_decide_solo_sus_activos(fabrica):
    movimiento = fabrica.movimiento(
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1", estado=I.PENDIENTE_RESPONSABLE),
            fabrica.item(activo_id="a2", responsable_original_id="u3", estado=I.PENDIENTE_RESPONSABLE),
        ]
    )
    item_de_u3 = movimiento.item("a2")

    assert acciones_de_item(movimiento, item_de_u3, "u1", EMPLEADO, "u3") == []
    assert acciones_de_item(movimiento, item_de_u3, "u3", EMPLEADO, "u3") == [A.APROBAR, A.RECHAZAR]


def test_tiene_el_activo_el_destinatario_o_su_responsable_actual(fabrica):
    movimiento = fabrica.movimiento(usuario_destino_id="u2")

    assert tiene_el_activo(movimiento, "u2", "u2") is True
    assert tiene_el_activo(movimiento, "u5", "u5") is True
    assert tiene_el_activo(movimiento, "u1", "u5") is False
    assert tiene_el_activo(movimiento, "u1", None) is False


# --- visibilidad ---


def test_ven_el_movimiento_el_admin_quien_lo_creo_el_destinatario_y_los_responsables(fabrica):
    movimiento = fabrica.movimiento(
        creado_por=fabrica.audit("u5", "Creador"),
        usuario_destino_id="u2",
        items=[fabrica.item(activo_id="a1", responsable_original_id="u1")],
    )
    responsables = {"a1": "u4"}

    assert puede_ver(movimiento, "x", ADMIN, responsables) is True
    for relacionado in ("u5", "u2", "u1", "u4"):
        assert puede_ver(movimiento, relacionado, EMPLEADO, responsables) is True


def test_quien_no_tiene_relacion_no_ve_el_movimiento(fabrica):
    movimiento = fabrica.movimiento(creado_por=fabrica.audit("u5", "Creador"))

    assert puede_ver(movimiento, "u9", EMPLEADO, {"a1": "u1"}) is False


def test_el_responsable_de_cualquiera_de_los_activos_ve_el_movimiento(fabrica):
    movimiento = fabrica.movimiento(
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1"),
            fabrica.item(activo_id="a2", responsable_original_id="u3"),
        ]
    )

    assert puede_ver(movimiento, "u3", EMPLEADO, {"a1": "u1", "a2": "u3"}) is True


# --- actas ---


def test_acepta_el_acta_el_destinatario_y_una_sola_vez(fabrica):
    movimiento = fabrica.movimiento(usuario_destino_id="u2")
    pendiente = fabrica.acta()
    aceptada = fabrica.acta(aceptada_por=fabrica.sello("u2", "Destino", "d@example.com"))

    assert puede_aceptar_acta(movimiento, pendiente, "u2") is True
    assert puede_aceptar_acta(movimiento, pendiente, "u1") is False
    assert puede_aceptar_acta(movimiento, pendiente, "admin") is False
    assert puede_aceptar_acta(movimiento, aceptada, "u2") is False


def test_aceptar_acta_aparece_entre_las_acciones_del_destinatario_mientras_haya_un_acta_pendiente(fabrica):
    item = fabrica.item(estado=I.EN_CURSO)
    movimiento = fabrica.movimiento(
        items=[item], usuario_destino_id="u2", estado=E.EN_CURSO, actas=[fabrica.acta()]
    )

    assert A.ACEPTAR_ACTA in acciones_permitidas(movimiento, "u2", EMPLEADO, {"a1": "u2"})
    assert A.ACEPTAR_ACTA not in acciones_permitidas(movimiento, "admin", ADMIN, {"a1": "u2"})


def test_sin_actas_no_hay_nada_que_aceptar(fabrica):
    item = fabrica.item(estado=I.EN_CURSO)
    movimiento = fabrica.movimiento(items=[item], usuario_destino_id="u2", estado=E.EN_CURSO)

    assert A.ACEPTAR_ACTA not in acciones_permitidas(movimiento, "u2", EMPLEADO, {"a1": "u2"})
