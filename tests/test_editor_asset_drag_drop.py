from pathlib import Path
from nexora.editor.commands.asset_commands import texture_source_for_assets
from nexora.scene import Scene
from nexora.scene.serialization.registry import NodeFactoryRegistry

class FakeTexture:
    width=128; height=64
class FakeAssets:
    def __init__(self,root): self.root=root; self.loaded=[]
    def texture(self,source): self.loaded.append(str(source)); return FakeTexture()

def test_texture_source_relative_to_asset_root(tmp_path: Path):
    root=tmp_path/"assets"; image=root/"sprites"/"hero.png"; image.parent.mkdir(parents=True); image.write_bytes(b"x")
    assert texture_source_for_assets(image, FakeAssets(root.resolve())) == "sprites/hero.png"

def test_animated_sprite_registered():
    assert "AnimatedSprite" in NodeFactoryRegistry().registered_type_ids()

def test_animated_sprite_round_trip(tmp_path: Path):
    assets=FakeAssets((tmp_path/"assets").resolve()); scene=Scene("x"); registry=NodeFactoryRegistry()
    sprite=registry.create("AnimatedSprite","Hero",scene.world,context={"assets":assets})
    sprite._nexora_texture_source="sprites/hero.png"; sprite.texture=FakeTexture(); sprite.width=128.0; sprite.height=64.0; sprite.alpha=.75; sprite.flip_x=True
    state=registry.dump_properties(sprite)
    clone=registry.create("AnimatedSprite","Clone",scene.world,context={"assets":assets}); registry.load_properties(clone,state,context={"assets":assets})
    assert clone.width==128.0 and clone.height==64.0 and clone.alpha==.75 and clone.flip_x is True
    assert clone._nexora_texture_source=="sprites/hero.png" and assets.loaded[-1]=="sprites/hero.png"
