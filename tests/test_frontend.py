import pytest
from playwright.sync_api import Page, expect
import time

BASE_URL = "https://voltrace-game.onrender.com"

def test_titulo_pagina(page: Page):
    page.goto(BASE_URL)
    expect(page).to_have_title("VoltRace Online")

def test_flujo_completo_registro_login(page: Page):
    semilla = int(time.time())
    usuario = f"Bot{semilla}"
    email = f"bot{semilla}@test.com"
    password = "password123" 

    print(f"\n🌍 Iniciando prueba E2E con: {usuario}")

    page.goto(BASE_URL)
    page.locator("text=Registrarse").click()
    expect(page.get_by_role("heading", name="Crear Cuenta")).to_be_visible()

    page.locator("#register-username").fill(usuario)
    page.locator("#register-email").fill(email)
    page.locator("#register-password").fill(password)
    page.get_by_role("button", name="Crear Cuenta").click()

    btn_crear_sala = page.get_by_role("button", name="Crear Sala")
    expect(btn_crear_sala).to_be_visible(timeout=30000)
    expect(page.get_by_text(usuario)).to_be_visible()
    print("✅ Registro exitoso.")

    page.get_by_role("button", name="Cerrar Sesión").click()
    expect(page.locator("text=Iniciar Sesión").first).to_be_visible()
    print("✅ Logout exitoso.")

    page.locator("text=Iniciar Sesión").first.click()
    expect(page.get_by_role("heading", name="Iniciar Sesión")).to_be_visible()

    page.locator("#login-email").fill(email)
    page.locator("#login-password").fill(password)
    page.get_by_role("button", name="Entrar").click()

    expect(btn_crear_sala).to_be_visible(timeout=30000)
    expect(page.get_by_text(usuario)).to_be_visible()
    print("✅ Login exitoso.")

def test_login_fallido_visual(page: Page):
    page.goto(BASE_URL)

    # Asegurar pestaña Login
    page.locator("text=Iniciar Sesión").first.click()
    expect(page.get_by_role("heading", name="Iniciar Sesión")).to_be_visible()

    # Llenar con datos falsos
    page.locator("#login-email").fill("usuario@falso.com")
    page.locator("#login-password").fill("contraseñamal")

    # Enviar
    page.get_by_role("button", name="Entrar").click()

    mensaje_error = page.locator("text=Email o contraseña incorrectos")
    
    expect(mensaje_error).to_be_visible(timeout=20000)

def test_flujo_crear_sala_visual(page: Page):
    semilla = int(time.time())
    usuario = f"SalaBot{semilla}"
    email = f"sala{semilla}@test.com"
    password = "password123"

    page.goto(BASE_URL)
    page.locator("text=Registrarse").click()
    expect(page.get_by_role("heading", name="Crear Cuenta")).to_be_visible()
    
    page.locator("#register-username").fill(usuario)
    page.locator("#register-email").fill(email)
    page.locator("#register-password").fill(password)
    page.get_by_role("button", name="Crear Cuenta").click()

    # Esperar a estar en el Lobby
    btn_crear = page.get_by_role("button", name="Crear Sala")
    expect(btn_crear).to_be_visible(timeout=30000)

    # Crear Sala
    btn_crear.click()

    # Cambio de Pantalla
    titulo_sala = page.locator("h2", has_text="Sala:")
    expect(titulo_sala).to_be_visible(timeout=15000)
    
    # Verificar que el botón "Iniciar Juego" esté presente
    expect(page.get_by_role("button", name="Iniciar Juego")).to_be_visible()