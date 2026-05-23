import logging
from pathlib import Path


logger = logging.getLogger(__name__)

SUPPORTED_ASSET_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def resolve_asset_path(assets_dir: Path, basename: str) -> Path:
    base_path = assets_dir / basename
    if base_path.suffix:
        return base_path
    for extension in SUPPORTED_ASSET_EXTENSIONS:
        candidate = assets_dir / f"{basename}{extension}"
        if candidate.exists():
            return candidate
    return assets_dir / f"{basename}.jpg"


async def send_asset(
    bot,
    asset_path: Path,
    fallback_name: str | None = None,
    caption: str | None = None,
    parse_mode: str | None = None,
    **chat_kwargs,
) -> None:
    if not chat_kwargs:
        return
    if not asset_path.exists():
        logger.error(f"Asset file does not exist: {asset_path}")
        await bot.send_message(text=f"Файл не найден: {fallback_name or asset_path.name}", **chat_kwargs)
        return

    media_kwargs = dict(chat_kwargs)
    if caption is not None:
        media_kwargs["caption"] = caption
    if parse_mode is not None:
        media_kwargs["parse_mode"] = parse_mode

    with asset_path.open("rb") as asset:
        if asset_path.suffix.lower() == ".gif":
            await bot.send_animation(animation=asset, **media_kwargs)
        else:
            await bot.send_photo(photo=asset, **media_kwargs)
