from django.apps import AppConfig
import os


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        try:
            from PIL import Image
            from django.conf import settings

            artifacts_dir = r"C:\Users\aadar\.gemini\antigravity-ide\brain\c1a045ed-4bbe-4a21-9c4e-2d84b8afd70c"
            base_static = os.path.join(settings.BASE_DIR, "static", "images")
            games_static = os.path.join(base_static, "games")
            defaults_static = os.path.join(base_static, "defaults")
            hero_static = os.path.join(base_static, "hero")

            os.makedirs(games_static, exist_ok=True)
            os.makedirs(defaults_static, exist_ok=True)
            os.makedirs(hero_static, exist_ok=True)

            mapping = {
                "pubg_mobile_artwork_1786954123953.png": "pubg",
                "ea_fc_artwork_1786954145432.png": "eafc",
                "valorant_artwork_1786954182210.png": "valorant",
                "cs2_artwork_1786954312318.png": "cs2",
                "free_fire_artwork_1786954385669.png": "free_fire",
                "rocket_league_artwork_1786954412123.png": "rocket_league",
                "dota2_artwork_1786954574490.png": "dota2",
            }

            for src_filename, game_key in mapping.items():
                src_path = os.path.join(artifacts_dir, src_filename)
                if os.path.exists(src_path):
                    webp_path = os.path.join(games_static, f"{game_key}.webp")
                    png_path = os.path.join(games_static, f"{game_key}.png")
                    if not os.path.exists(webp_path) or not os.path.exists(png_path):
                        img = Image.open(src_path)
                        img.save(webp_path, "WEBP", quality=90, optimize=True)
                        img.save(png_path, "PNG", optimize=True)

            hero_src = os.path.join(artifacts_dir, "esports_hero_arena_1786954693272.png")
            if os.path.exists(hero_src):
                hero_webp_1 = os.path.join(hero_static, "gamearena_hero.webp")
                hero_webp_2 = os.path.join(base_static, "hero.webp")
                if not os.path.exists(hero_webp_1) or not os.path.exists(hero_webp_2):
                    img = Image.open(hero_src)
                    img.save(hero_webp_1, "WEBP", quality=90, optimize=True)
                    img.save(hero_webp_2, "WEBP", quality=90, optimize=True)

                cover_webp = os.path.join(defaults_static, "tournament_cover.webp")
                banner_webp = os.path.join(defaults_static, "tournament_banner.webp")
                game_def_webp = os.path.join(defaults_static, "game_default.webp")
                team_def_webp = os.path.join(defaults_static, "team_default.webp")

                if not os.path.exists(cover_webp):
                    img = Image.open(hero_src)
                    img.save(cover_webp, "WEBP", quality=88, optimize=True)
                if not os.path.exists(banner_webp):
                    img = Image.open(hero_src)
                    img.save(banner_webp, "WEBP", quality=88, optimize=True)
                if not os.path.exists(game_def_webp):
                    img = Image.open(hero_src)
                    img.save(game_def_webp, "WEBP", quality=88, optimize=True)
                if not os.path.exists(team_def_webp):
                    img = Image.open(hero_src)
                    img.save(team_def_webp, "WEBP", quality=88, optimize=True)
        except Exception:
            pass