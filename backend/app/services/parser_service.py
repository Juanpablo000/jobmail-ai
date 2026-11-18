"""
ParserService — Hito 2
Extrae campos estructurados de correos HTML de LinkedIn y Computrabajo.

IMPORTANTE: El HTML crudo se recibe en memoria y se descarta tras el parsing.
NUNCA se guarda en la base de datos.

Estrategia de parsing:
  - Múltiples estrategias por plataforma (A → B → C fallback)
  - Tolerante a fallos: errores por oferta individual, nunca aborta todo
  - Un email puede tener múltiples ofertas → retorna lista
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Remitentes para detección de plataforma
_PLATFORM_SENDERS = {
    "linkedin": ["linkedin.com", "linkedin."],
    "computrabajo": ["computrabajo.com", "computrabajo."],
}

JUNK_TITLES = {
    "revisa las vacantes", "aviso legal", "contactar", "modificar alerta",
    "política de privacidad", "términos y condiciones", "darme de baja",
    "ver más", "ver oferta", "ver ofertas", "postularme", "descargar app",
    "configurar alertas", "cerrar sesión", "ayuda", "unsubscribe",
    "manage alerts", "privacy policy", "terms of service", "descarga la app",
}


@dataclass
class ParsedOffer:
    """Oferta laboral extraída de un correo. Todos los campos excepto title son opcionales."""
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    offer_url: Optional[str] = None
    published_at: Optional[datetime] = None
    platform: str = "otro"


class ParserService:
    """Parsea correos HTML de plataformas de empleo y extrae ofertas laborales."""

    # ── Detección de plataforma ───────────────────────────────────────────────

    def detect_platform(self, sender_email: str) -> str:
        """Detecta plataforma por email del remitente."""
        sender_lower = sender_email.lower()
        for platform, patterns in _PLATFORM_SENDERS.items():
            if any(p in sender_lower for p in patterns):
                return platform
        return "otro"

    # ── Dispatcher principal ──────────────────────────────────────────────────

    def parse(self, html_body: str, platform: str, email_received_at: datetime) -> list[ParsedOffer]:
        """
        Parsea el HTML del correo y retorna lista de ofertas extraídas.
        Nunca lanza excepción: errores se loggean y retorna lista vacía.
        """
        if not html_body or not html_body.strip():
            logger.warning("HTML vacío recibido para parsear")
            return []

        try:
            soup = BeautifulSoup(html_body, "lxml")
        except Exception as e:
            logger.error(f"Error parseando HTML con lxml, intentando html.parser: {e}")
            try:
                soup = BeautifulSoup(html_body, "html.parser")
            except Exception as e2:
                logger.error(f"Error crítico parseando HTML: {e2}")
                return []

        try:
            if platform == "linkedin":
                offers = self._parse_linkedin(soup)
            elif platform == "computrabajo":
                offers = self._parse_computrabajo(soup)
            else:
                offers = self._parse_generic(soup)

            # Asignar plataforma y limpiar
            valid_offers = []
            for offer in offers:
                offer.platform = platform
                clean_title = (offer.title or "").strip()
                if not clean_title or len(clean_title) < 4:
                    continue
                if clean_title.lower() in JUNK_TITLES:
                    continue

                if platform == "computrabajo":
                    self._clean_computrabajo_offer(offer)
                elif platform == "linkedin":
                    self._clean_linkedin_offer(offer)

                if offer.title and len(offer.title.strip()) >= 3 and offer.title.lower().strip() not in JUNK_TITLES:
                    valid_offers.append(offer)

            logger.info(f"Parser [{platform}]: {len(valid_offers)} ofertas válidas extraídas")
            return valid_offers

        except Exception as e:
            logger.error(f"Error inesperado en parser [{platform}]: {e}", exc_info=True)
            return []

    def _clean_computrabajo_offer(self, offer: ParsedOffer) -> None:
        """Desglosa y limpia textos concatenados típicos de Computrabajo."""
        t = offer.title
        # 1. Quitar prefijos comerciales
        t = re.sub(r"^(?:Salario \d+% superior al promedio|Oferta con alta revisión de HV)\s*", "", t, flags=re.I)

        # 2. Extraer salario si está incrustado en el título
        sal_match = re.search(r"(\$\s*[\d\.,]+(?:\s*\(Mensual\))?)", t)
        if sal_match:
            if not offer.salary:
                offer.salary = sal_match.group(1).strip()
            t = t[:sal_match.start()] + t[sal_match.end():]

        # 3. Quitar antigüedad temporal al final
        t = re.sub(r"\s*(?:Hace \d+ días?|Ayer|Hoy)(?:\s*\(actualizada\))?\s*$", "", t, flags=re.I)

        # 4. Extraer ciudad si está al final
        loc_match = re.search(r"((?:Medellín|Bogotá|Cali|Barranquilla|Envigado|Sabaneta|Itagüí|Rionegro|Bello|Copacabana|La Estrella|Guarne|Girardota|Jericó|Remoto|Bogota|Medellin)(?:,\s*[A-Za-zñáéíóúÁÉÍÓÚ\s]+)?)$", t, flags=re.I)
        if loc_match:
            if not offer.location:
                offer.location = loc_match.group(1).strip()
            t = t[:loc_match.start()].strip()

        # 5. Rating y separar título / empresa
        rating_match = re.search(r"(\d\.\d)\s*", t)
        if rating_match:
            if not offer.company:
                offer.company = t[rating_match.end():].strip()
            t = t[:rating_match.start()].strip()
        else:
            split_match = re.search(r"([a-zñáéíóú])\s+([A-ZÁÉÍÓÚ\s]{3,}(?:S\.?A\.?S?|LTDA|S\.?A\.?|INC)?)$", t)
            if split_match:
                if not offer.company:
                    offer.company = split_match.group(2).strip()
                t = t[:split_match.start(2)].strip()

        offer.title = t.strip()

    def _clean_linkedin_offer(self, offer: ParsedOffer) -> None:
        """Limpia metadatos y separa ubicación en ofertas de LinkedIn."""
        t = offer.title
        if " · " in t:
            left, right = t.split(" · ", 1)
            right_clean = re.sub(r"\s*(?:Solicitud sencilla|En busca de personal|\d+ (?:personas?|antiguos?).*)$", "", right, flags=re.I).strip()
            if right_clean and not offer.location:
                offer.location = right_clean
            t = left.strip()
        else:
            t = re.sub(r"\s*(?:Solicitud sencilla|En busca de personal|\d+ (?:personas?|antiguos?).*)$", "", t, flags=re.I).strip()

        offer.title = t.strip()

    # ── Parser LinkedIn ───────────────────────────────────────────────────────

    def _parse_linkedin(self, soup: BeautifulSoup) -> list[ParsedOffer]:
        """
        Parser para emails de LinkedIn Job Alerts.
        Los correos de LinkedIn contienen links a ofertas con patrones conocidos.
        Estrategia A → B → C con fallback progresivo.
        """
        offers = []

        # Estrategia A: Links directos a linkedin.com/jobs/view/ o /comm/jobs/view/
        job_patterns = [
            r"linkedin\.com/jobs/view/",
            r"linkedin\.com/comm/jobs/view/",
            r"linkedin\.com/jobs/collections/",
        ]
        job_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if any(re.search(p, href) for p in job_patterns):
                job_links.append(a_tag)

        if job_links:
            logger.debug(f"LinkedIn Estrategia A: {len(job_links)} links de ofertas")
            for a_tag in job_links:
                title = self._clean_text(a_tag.get_text())
                if not title or len(title) < 3:
                    # El título puede estar en el elemento padre
                    parent = a_tag.find_parent(["td", "div", "span", "p"])
                    if parent:
                        title = self._clean_text(parent.get_text())

                if not title or len(title) < 3:
                    continue

                url = self._clean_url(a_tag["href"], "linkedin")
                company, location = self._extract_company_location_near(a_tag)

                offers.append(ParsedOffer(
                    title=title,
                    company=company,
                    location=location,
                    offer_url=url,
                ))
            if offers:
                return offers

        # Estrategia B: Buscar contenedores con clases relacionadas a empleo
        job_containers = soup.find_all(
            ["td", "div", "table"],
            attrs={"class": re.compile(r"job|position|listing|card|offer|vacancy", re.I)},
        )
        if job_containers:
            logger.debug(f"LinkedIn Estrategia B: {len(job_containers)} contenedores")
            for container in job_containers:
                link = container.find("a", href=True)
                if not link:
                    continue
                title = self._clean_text(link.get_text() or container.get_text())
                if not title or len(title) < 3:
                    continue
                url = self._clean_url(link["href"], "linkedin")
                company, location = self._extract_company_location_near(link)
                offers.append(ParsedOffer(title=title, company=company, location=location, offer_url=url))
            if offers:
                return offers

        # Estrategia C (fallback): Todos los links que apunten a linkedin.com
        logger.debug("LinkedIn Estrategia C (fallback genérico)")
        seen_urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if "linkedin.com" not in href:
                continue
            # Filtrar links de navegación (perfil, unsubscribe, etc.)
            skip_patterns = ["unsubscribe", "settings", "profile", "mynetwork", "messaging", "notifications"]
            if any(p in href.lower() for p in skip_patterns):
                continue

            title = self._clean_text(a_tag.get_text())
            if not title or len(title) < 5:
                continue

            url = self._clean_url(href, "linkedin")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            company, location = self._extract_company_location_near(a_tag)
            offers.append(ParsedOffer(title=title, company=company, location=location, offer_url=url))

        return offers

    # ── Parser Computrabajo ───────────────────────────────────────────────────

    def _parse_computrabajo(self, soup: BeautifulSoup) -> list[ParsedOffer]:
        """
        Parser para emails de Computrabajo.
        Estrategia A → B → C con fallback.
        """
        offers = []

        # Estrategia A: Links que apuntan a computrabajo.com con texto de oferta
        ct_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if "computrabajo.com" in href and a_tag.get_text(strip=True):
                # Filtrar links de navegación
                skip = ["unsubscribe", "baja", "cancelar", "contacto", "privacidad", "terminos"]
                if any(s in href.lower() for s in skip):
                    continue
                ct_links.append(a_tag)

        if ct_links:
            logger.debug(f"Computrabajo Estrategia A: {len(ct_links)} links")
            seen_urls = set()
            for a_tag in ct_links:
                title = self._clean_text(a_tag.get_text())
                if not title or len(title) < 5:
                    # Buscar título en el elemento padre
                    parent = a_tag.find_parent(["td", "div", "li"])
                    if parent:
                        # Buscar el texto más prominente (h1-h4, strong, b)
                        heading = parent.find(["h1", "h2", "h3", "h4", "strong", "b"])
                        if heading:
                            title = self._clean_text(heading.get_text())
                        else:
                            title = self._clean_text(parent.get_text())

                if not title or len(title) < 5:
                    continue

                url = self._clean_url(a_tag["href"], "computrabajo")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                company, location = self._extract_company_location_near(a_tag)
                salary = self._extract_salary_near(a_tag)

                offers.append(ParsedOffer(
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    offer_url=url,
                ))
            if offers:
                return offers

        # Estrategia B: Contenedores con clase relacionada a oferta
        containers = soup.find_all(
            ["td", "div", "li"],
            attrs={"class": re.compile(r"oferta|empleo|trabajo|job|vacante|cargo", re.I)},
        )
        if containers:
            logger.debug(f"Computrabajo Estrategia B: {len(containers)} contenedores")
            for container in containers:
                link = container.find("a", href=True)
                title_tag = container.find(["h1", "h2", "h3", "h4", "strong", "b"])
                title = self._clean_text(
                    (title_tag.get_text() if title_tag else None)
                    or (link.get_text() if link else None)
                    or container.get_text()
                )
                if not title or len(title) < 5:
                    continue
                url = self._clean_url(link["href"], "computrabajo") if link else None
                company, location = self._extract_company_location_near(container)
                salary = self._extract_salary_near(container)
                offers.append(ParsedOffer(title=title, company=company, location=location, salary=salary, offer_url=url))
            if offers:
                return offers

        # Estrategia C: Regex sobre texto plano del correo
        logger.debug("Computrabajo Estrategia C (regex sobre texto plano)")
        full_text = soup.get_text(separator="\n")
        # Buscar bloques con patrón: Título de oferta seguido de empresa/ubicación
        blocks = re.split(r"\n{2,}", full_text)
        for block in blocks:
            block = block.strip()
            if len(block) < 10 or len(block) > 500:
                continue
            # Buscar empresa
            company_match = re.search(r"(?:Empresa|Compañía|Company):\s*(.+)", block, re.I)
            location_match = re.search(r"(?:Ciudad|Ubicación|Location|Lugar):\s*(.+)", block, re.I)
            salary_match = re.search(r"(?:Salario|Sueldo|Salary):\s*(.+)", block, re.I)
            # La primera línea no vacía como título
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if lines and len(lines[0]) > 5:
                offers.append(ParsedOffer(
                    title=lines[0],
                    company=self._clean_text(company_match.group(1)) if company_match else None,
                    location=self._clean_text(location_match.group(1)) if location_match else None,
                    salary=self._clean_text(salary_match.group(1)) if salary_match else None,
                ))

        return offers

    # ── Parser genérico ───────────────────────────────────────────────────────

    def _parse_generic(self, soup: BeautifulSoup) -> list[ParsedOffer]:
        """Fallback genérico para plataformas no reconocidas."""
        offers = []
        seen = set()
        for a_tag in soup.find_all("a", href=True):
            title = self._clean_text(a_tag.get_text())
            if not title or len(title) < 10:
                continue
            # Filtrar links genéricos (unsubscribe, home, etc.)
            href = a_tag.get("href", "")
            if any(p in href.lower() for p in ["unsubscribe", "mailto:", "javascript:"]):
                continue
            if title in seen:
                continue
            seen.add(title)
            company, location = self._extract_company_location_near(a_tag)
            offers.append(ParsedOffer(title=title, company=company, location=location, offer_url=href))
        return offers

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_company_location_near(self, element) -> tuple[Optional[str], Optional[str]]:
        """
        Intenta extraer empresa y ubicación del contexto cercano a un elemento.
        Busca en el padre, hermanos y texto adyacente.
        """
        company = None
        location = None

        # Buscar en el elemento padre y sus hijos directos
        parent = element.find_parent(["td", "div", "li", "tr", "table"])
        if parent:
            text = parent.get_text(separator=" | ")
            # Patrones comunes en correos de empleo
            company_match = re.search(
                r"(?:empresa|company|compañía|empleador)[:\s]+([^\|•\n]{3,60})",
                text, re.I
            )
            location_match = re.search(
                r"(?:ciudad|ubicación|location|lugar|sede)[:\s]+([^\|•\n]{3,60})",
                text, re.I
            )

            if company_match:
                company = self._clean_text(company_match.group(1))
            if location_match:
                location = self._clean_text(location_match.group(1))

            # Si no hay match con etiqueta, buscar patrones de ubicación conocidos
            if not location:
                # Ciudades colombianas comunes y patrones de ubicación
                loc_match = re.search(
                    r"\b(Bogotá|Medellín|Cali|Barranquilla|Cartagena|Bucaramanga|"
                    r"Pereira|Manizales|Cúcuta|Ibagué|Remoto|Remote|Colombia|"
                    r"Bogota|Medellin|Virtual|Híbrido|Hybrid)\b",
                    text, re.I
                )
                if loc_match:
                    location = loc_match.group(0)

        return company, location

    def _extract_salary_near(self, element) -> Optional[str]:
        """Extrae información de salario del contexto cercano."""
        parent = element.find_parent(["td", "div", "li", "tr"])
        if not parent:
            return None
        text = parent.get_text(separator=" ")
        return self._extract_salary(text)

    def _extract_salary(self, text: str) -> Optional[str]:
        """Extrae salario de un texto usando regex."""
        patterns = [
            r"\$\s*[\d\.,]+(?:\s*[-–]\s*\$?\s*[\d\.,]+)?(?:\s*(?:COP|USD|MXN|mensual|mes))?",
            r"[\d\.,]+\s*(?:millones?|mil)\s*(?:de pesos?|COP)?",
            r"COP\s*[\d\.,]+(?:\s*[-–]\s*[\d\.,]+)?",
            r"(?:salario|sueldo)[:\s]+([^\n•|]{5,50})",
            r"(?:A convenir|Por convenir|No especificado|Según experiencia)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return self._clean_text(match.group(0))
        return None

    def _clean_url(self, url: str, platform: str) -> str:
        """
        Limpia URLs de tracking y parámetros innecesarios.
        Para LinkedIn: conserva hasta el ID de la oferta.
        Para Computrabajo: elimina parámetros de tracking.
        """
        if not url:
            return url

        try:
            # Manejar URLs de redirección (tracking links)
            # Buscar la URL real dentro del parámetro de redirección
            redirect_match = re.search(r"[?&](?:url|redirect|dest|target)=([^&]+)", url, re.I)
            if redirect_match:
                from urllib.parse import unquote
                url = unquote(redirect_match.group(1))

            parsed = urlparse(url)

            if platform == "linkedin":
                # Para LinkedIn jobs, conservar solo el path hasta el ID
                path = parsed.path
                # Limpiar path: /jobs/view/1234567890/
                path_match = re.match(r"(/(?:jobs|comm/jobs)/(?:view|collections)/\d+)", path)
                if path_match:
                    return f"https://www.linkedin.com{path_match.group(1)}"
                # Si no tiene el patrón exacto, eliminar query string
                return urlunparse(parsed._replace(query="", fragment=""))

            elif platform == "computrabajo":
                # Eliminar parámetros de tracking
                return urlunparse(parsed._replace(query="", fragment=""))

            else:
                return urlunparse(parsed._replace(query="", fragment=""))

        except Exception:
            return url

    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Limpia texto: strip, colapsa whitespace múltiple."""
        if not text:
            return None
        cleaned = re.sub(r"\s+", " ", text).strip()
        # Eliminar caracteres de control
        cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)
        return cleaned if cleaned and len(cleaned) >= 2 else None
