"""Random human-like browser actions to reduce bot detection fingerprint."""
import asyncio
import random
from typing import Optional

from playwright.async_api import Page, Locator


# Nearby keys on a QWERTY keyboard for realistic typos
NEARBY_KEYS = {
    'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'sfce', 'e': 'wrd',
    'f': 'dgcv', 'g': 'fhtb', 'h': 'gjyn', 'i': 'uok', 'j': 'hkun',
    'k': 'jloi', 'l': 'kop', 'm': 'njk', 'n': 'bmhj', 'o': 'iplk',
    'p': 'ol', 'q': 'wa', 'r': 'etf', 's': 'adwz', 't': 'ryg',
    'u': 'yij', 'v': 'cfgb', 'w': 'qeas', 'x': 'zsdc', 'y': 'tuh',
    'z': 'xas',
}


class HumanBehavior:
    """Injects random human-like actions between real bot steps.

    All randomness parameters (probability, action selection, timing) are
    themselves randomized so the pattern is never predictable.
    """

    def __init__(self, page: Page, intensity: float = 0.5, enabled: bool = True):
        """
        Args:
            page: Active Playwright page.
            intensity: 0.0–1.0 scaling factor for how often actions trigger.
                       0.0 = never, 1.0 = ~40 % chance per call.
            enabled: When False, all human-like behaviour is skipped (no-op).
        """
        self.page = page
        self.intensity = max(0.0, min(1.0, intensity))
        self.enabled = enabled
        self._action_count = 0

    def update_page(self, page: Page):
        """Update the page reference (e.g. after tab switch)."""
        self.page = page

    # ------------------------------------------------------------------
    # Public API – call these from scraper / filler code
    # ------------------------------------------------------------------

    async def maybe_act(self):
        """Randomly decide whether to perform 0-2 tiny human-like actions.

        Designed to be sprinkled liberally; most calls return instantly.
        Total added latency is capped at ~2 s per invocation on average.
        """
        if not self.enabled:
            return
        if random.random() > 0.40 * self.intensity:
            return

        actions = [
            self._random_mouse_move,
            self._random_micro_pause,
            self._click_empty_area,
            self._small_scroll_jitter,
        ]

        how_many = random.choices([1, 2], weights=[75, 25])[0]
        chosen = random.sample(actions, min(how_many, len(actions)))
        for action in chosen:
            try:
                await action()
            except Exception:
                pass

        self._action_count += 1

    async def maybe_act_form(self):
        """Variant tuned for form pages – also considers checkbox toggles."""
        if not self.enabled:
            return
        if random.random() > 0.35 * self.intensity:
            return

        actions = [
            self._random_mouse_move,
            self._random_micro_pause,
            self._click_empty_area,
            self._small_scroll_jitter,
            self._accidental_checkbox_toggle,
        ]

        # Checkbox toggle should be rare
        weights = [30, 25, 20, 20, 5]
        chosen = random.choices(actions, weights=weights, k=1)
        for action in chosen:
            try:
                await action()
            except Exception:
                pass

        self._action_count += 1

    async def type_with_mistakes(
        self,
        locator: Locator,
        text: str,
        mistake_prob: float = 0.08,
        base_delay_min: int = 40,
        base_delay_max: int = 160,
    ):
        """Type into a field character-by-character, occasionally making
        typos (wrong key from neighbours) then backspacing to fix them.

        When disabled, falls back to a simple ``locator.fill(text)``.

        Args:
            locator: Target input/textarea locator.
            text: Text to ultimately type.
            mistake_prob: Per-character probability of a typo.
            base_delay_min: Min ms delay between keystrokes.
            base_delay_max: Max ms delay between keystrokes.
        """
        if not self.enabled:
            await locator.fill(text)
            return

        await locator.click()
        await asyncio.sleep(random.uniform(0.1, 0.35))

        for char in text:
            should_typo = random.random() < (mistake_prob * self.intensity)

            if should_typo and char.lower() in NEARBY_KEYS:
                wrong_char = random.choice(NEARBY_KEYS[char.lower()])
                if char.isupper():
                    wrong_char = wrong_char.upper()

                await self.page.keyboard.type(
                    wrong_char, delay=random.randint(base_delay_min, base_delay_max)
                )
                await asyncio.sleep(random.uniform(0.15, 0.55))
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.2))

            await self.page.keyboard.type(
                char, delay=random.randint(base_delay_min, base_delay_max)
            )

            # Occasional micro-pause mid-typing (thinking)
            if random.random() < 0.04:
                await asyncio.sleep(random.uniform(0.3, 0.9))

    # ------------------------------------------------------------------
    # Individual random micro-actions (all very short)
    # ------------------------------------------------------------------

    async def _random_mouse_move(self):
        """Move the mouse to a random visible area of the viewport."""
        vp = self.page.viewport_size or {"width": 1280, "height": 800}
        x = random.randint(50, vp["width"] - 50)
        y = random.randint(50, vp["height"] - 50)
        await self.page.mouse.move(x, y, steps=random.randint(3, 10))
        await asyncio.sleep(random.uniform(0.05, 0.25))

    async def _random_micro_pause(self):
        """Brief pause as if the user is reading."""
        await asyncio.sleep(random.uniform(0.2, 1.2))

    async def _click_empty_area(self):
        """Click on a safe blank region (top-right or bottom area)."""
        vp = self.page.viewport_size or {"width": 1280, "height": 800}
        regions = [
            (vp["width"] - random.randint(20, 80), random.randint(10, 40)),
            (random.randint(20, 80), vp["height"] - random.randint(10, 40)),
            (vp["width"] // 2 + random.randint(-100, 100), vp["height"] - random.randint(5, 25)),
        ]
        x, y = random.choice(regions)
        await self.page.mouse.click(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _small_scroll_jitter(self):
        """Scroll down a little then back up (or vice versa)."""
        delta = random.randint(60, 250)
        direction = random.choice([1, -1])
        await self.page.mouse.wheel(0, delta * direction)
        await asyncio.sleep(random.uniform(0.2, 0.6))
        await self.page.mouse.wheel(0, -delta * direction)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _accidental_checkbox_toggle(self):
        """Find a visible checkbox, check it, pause, then uncheck it."""
        try:
            checkboxes = self.page.locator(
                "input[type='checkbox'], material-checkbox, [role='checkbox']"
            )
            count = await checkboxes.count()
            if count == 0:
                return

            idx = random.randint(0, count - 1)
            cb = checkboxes.nth(idx)
            if not await cb.is_visible(timeout=500):
                return

            await cb.click()
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await cb.click()
            await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass
