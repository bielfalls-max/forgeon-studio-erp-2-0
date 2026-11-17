"""Regras compartilhadas para consulta e exportação dos mesmos registros."""
from .numbers import norm
import json

def date_matches(value,filters):
    value=str(value or '')[:10]
    return (not filters.get('start') or value>=filters['start']) and (not filters.get('end') or value<=filters['end'])

def recipe_matches(recipe,filters):
    colors=recipe.get('colors',[])
    return any((not filters.get('material') or norm(filters['material']) in norm(c['material'])) and (not filters.get('color') or norm(filters['color']) in norm(c['color'])) for c in colors) if filters.get('material') or filters.get('color') else True

def item_matches(item,filters):
    if filters.get('product') is not None and item['product_id']!=filters['product']:return False
    return recipe_matches(json.loads(item.get('usage_detail') or item.get('cost_detail') or '{}'),filters)
