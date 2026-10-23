"""Builds foods.json — the MVP food composition reference table.

Values are per 100 g edible portion. They were transcribed approximations of public
references and are flagged `verification: transcribed_unverified` until replaced by a
verified import (e.g. USDA FoodData Central CSV or Singapore HPB SG FoodID export).
GI values approximate the International Tables of Glycemic Index (Atkinson et al., 2021);
None means no supported GI value, so glycemic load is not estimated for that food.
"""
import json
from pathlib import Path

USDA = "USDA FoodData Central (SR Legacy / FNDDS), per 100 g"
HPB = "Singapore HPB Energy & Nutrient Composition of Food (per-serving values converted to per 100 g)"
GI_SRC = "International Tables of Glycemic Index (Atkinson et al., 2021), typical value"

# key, name, category, kcal, carb, prot, fat, sugar, fiber, sodium_mg, serving_g, serving_desc, gi, refined_carb, allergens, aliases, region
ROWS = [
 ("white_rice","White rice, steamed","grain",130,28.2,2.7,0.3,0.1,0.4,1,158,"1 cup",73,True,[],["rice","steamed rice","plain rice"],"generic"),
 ("brown_rice","Brown rice, cooked","grain",123,25.6,2.7,1.0,0.4,1.6,4,195,"1 cup",68,False,[],["brown rice"],"generic"),
 ("white_bread","White bread","grain",265,49.0,9.0,3.2,5.0,2.7,490,30,"1 slice",75,True,["gluten"],["bread","toast","white toast"],"generic"),
 ("french_bread","French bread / baguette","grain",274,52.0,11.0,3.0,5.0,2.2,600,64,"1 piece (~15 cm)",75,True,["gluten"],["baguette","french loaf"],"generic"),
 ("bagel","Bagel, plain","grain",250,48.9,10.0,1.5,6.0,2.1,439,105,"1 bagel",72,True,["gluten"],["bagel"],"generic"),
 ("pretzel","Soft pretzel, salted","grain",338,69.0,8.0,3.1,4.0,1.7,1100,115,"1 pretzel",83,True,["gluten"],["pretzel"],"generic"),
 ("pasta","Pasta / spaghetti, cooked","grain",158,31.0,5.8,0.9,0.6,1.8,1,140,"1 cup",49,True,["gluten"],["spaghetti","pasta","macaroni"],"generic"),
 ("egg_noodles","Egg noodles, cooked","grain",138,25.0,4.5,2.1,0.4,1.2,5,160,"1 cup",None,True,["gluten","egg"],["noodles","mee","egg noodle"],"generic"),
 ("oatmeal","Oatmeal (porridge, water)","grain",71,12.0,2.5,1.5,0.3,1.7,4,234,"1 cup",55,False,[],["oats","porridge","oatmeal"],"generic"),
 ("corn","Sweet corn, cooked","vegetable",96,21.0,3.4,1.5,4.5,2.4,1,100,"1 ear",52,False,[],["corn","sweet corn","corn on the cob"],"generic"),
 ("french_fries","French fries","vegetable",312,41.0,3.4,15.0,0.3,3.8,210,117,"1 medium serving",63,True,[],["fries","chips","french fries"],"generic"),
 ("mashed_potato","Mashed potato (milk, butter)","vegetable",113,17.0,1.9,4.2,1.5,1.5,330,210,"1 cup",78,True,["dairy"],["mashed potato","mashed potatoes"],"generic"),
 ("broccoli","Broccoli, cooked","vegetable",35,7.2,2.4,0.4,1.4,3.3,41,90,"1 cup",None,False,[],["broccoli"],"generic"),
 ("cauliflower","Cauliflower, cooked","vegetable",23,4.1,1.8,0.5,2.1,2.3,15,100,"1 cup",None,False,[],["cauliflower"],"generic"),
 ("cabbage","Cabbage, raw","vegetable",25,5.8,1.3,0.1,3.2,2.5,18,90,"1 cup shredded",None,False,[],["cabbage","head cabbage"],"generic"),
 ("cucumber","Cucumber","vegetable",15,3.6,0.7,0.1,1.7,0.5,2,100,"1/3 cucumber",None,False,[],["cucumber"],"generic"),
 ("bell_pepper","Bell pepper","vegetable",31,6.0,1.0,0.3,4.2,2.1,4,120,"1 medium",None,False,[],["capsicum","bell pepper"],"generic"),
 ("mushroom","Mushrooms","vegetable",22,3.3,3.1,0.3,2.0,1.0,5,70,"1 cup sliced",None,False,[],["mushroom","mushrooms"],"generic"),
 ("zucchini","Zucchini","vegetable",17,3.1,1.2,0.3,2.5,1.0,8,120,"1 cup",None,False,[],["zucchini","courgette"],"generic"),
 ("butternut_squash","Squash (butternut), cooked","vegetable",40,10.5,0.9,0.1,2.2,3.2,4,205,"1 cup",None,False,[],["squash","pumpkin","butternut"],"generic"),
 ("carrot","Carrot","vegetable",41,9.6,0.9,0.2,4.7,2.8,69,61,"1 medium",39,False,[],["carrot","carrots"],"generic"),
 ("artichoke","Artichoke, cooked","vegetable",53,12.0,2.9,0.3,1.0,8.6,60,120,"1 medium",None,False,[],["artichoke"],"generic"),
 ("green_salad","Mixed green salad (no dressing)","vegetable",17,3.3,1.2,0.2,1.2,1.8,28,85,"1.5 cups",None,False,[],["salad","green salad","lettuce","greens","vegetables"],"generic"),
 ("apple","Apple","fruit",52,13.8,0.3,0.2,10.4,2.4,1,182,"1 medium",36,False,[],["apple","granny smith"],"generic"),
 ("banana","Banana","fruit",89,22.8,1.1,0.3,12.2,2.6,1,118,"1 medium",51,False,[],["banana"],"generic"),
 ("orange","Orange","fruit",47,11.8,0.9,0.1,9.4,2.4,0,131,"1 medium",43,False,[],["orange"],"generic"),
 ("strawberry","Strawberries","fruit",32,7.7,0.7,0.3,4.9,2.0,1,150,"1 cup",40,False,[],["strawberry","strawberries"],"generic"),
 ("pineapple","Pineapple","fruit",50,13.1,0.5,0.1,9.9,1.4,1,165,"1 cup chunks",59,False,[],["pineapple"],"generic"),
 ("lemon","Lemon","fruit",29,9.3,1.1,0.3,2.5,2.8,2,58,"1 lemon",None,False,[],["lemon","lime"],"generic"),
 ("pomegranate","Pomegranate arils","fruit",83,18.7,1.7,1.2,13.7,4.0,3,87,"1/2 cup",None,False,[],["pomegranate"],"generic"),
 ("fig","Fig, fresh","fruit",74,19.2,0.8,0.3,16.3,2.9,1,50,"1 medium",None,False,[],["fig"],"generic"),
 ("jackfruit","Jackfruit","fruit",95,23.2,1.7,0.6,19.1,1.5,2,165,"1 cup",None,False,[],["jackfruit","nangka"],"sg"),
 ("custard_apple","Custard apple","fruit",101,25.2,1.7,0.6,None,2.4,4,100,"1/2 fruit",None,False,[],["custard apple","sugar apple"],"generic"),
 ("chicken_breast","Chicken breast, grilled","protein",165,0.0,31.0,3.6,0.0,0.0,74,120,"1 piece",None,False,[],["chicken","grilled chicken","chicken breast"],"generic"),
 ("salmon","Salmon, cooked","protein",206,0.0,22.0,12.4,0.0,0.0,61,120,"1 fillet",None,False,["fish"],["salmon","fish"],"generic"),
 ("sushi","Sushi (nigiri / maki, mixed)","mixed",145,28.0,5.8,0.9,3.5,0.8,450,200,"8 pieces",52,True,["fish","soy"],["sushi","maki","nigiri"],"generic"),
 ("beef_steak","Beef steak (sirloin), cooked","protein",201,0.0,29.0,9.5,0.0,0.0,60,150,"1 steak",None,False,[],["steak","beef"],"generic"),
 ("tofu","Tofu, firm","protein",144,2.8,17.3,8.7,0.6,2.3,14,120,"1/2 cup",None,False,["soy"],["tofu","beancurd","tauhu"],"generic"),
 ("fried_egg","Egg, fried","protein",196,0.8,13.6,14.8,0.4,0.0,207,46,"1 egg",None,False,["egg"],["fried egg","egg"],"generic"),
 ("boiled_egg","Egg, boiled","protein",155,1.1,12.6,10.6,1.1,0.0,124,50,"1 egg",None,False,["egg"],["boiled egg","hard boiled egg"],"generic"),
 ("meat_loaf","Meat loaf","mixed",185,8.0,13.0,11.0,3.0,0.4,420,150,"1 slice",None,False,["egg","gluten"],["meatloaf","meat loaf"],"generic"),
 ("pizza","Pizza, cheese","mixed",266,33.0,11.0,10.0,3.6,2.3,598,107,"1 slice",60,True,["gluten","dairy"],["pizza"],"generic"),
 ("cheeseburger","Cheeseburger","mixed",250,24.0,13.0,11.0,5.0,1.5,560,120,"1 burger",None,True,["gluten","dairy"],["burger","cheeseburger","hamburger"],"generic"),
 ("hot_dog","Hot dog in bun","mixed",247,18.0,10.0,15.0,4.0,0.8,670,98,"1 hot dog",None,True,["gluten"],["hot dog","hotdog"],"generic"),
 ("burrito","Burrito (beans and meat)","mixed",190,22.0,9.0,7.0,1.5,3.0,480,220,"1 burrito",None,True,["gluten","dairy"],["burrito"],"generic"),
 ("sandwich","Sandwich (ham and cheese)","mixed",235,25.0,13.0,9.0,3.5,1.6,720,150,"1 sandwich",None,True,["gluten","dairy"],["sandwich"],"generic"),
 ("carbonara","Spaghetti carbonara","mixed",190,22.0,8.0,8.0,1.0,1.0,300,300,"1 plate",None,True,["gluten","egg","dairy"],["carbonara"],"generic"),
 ("pot_pie","Chicken pot pie","mixed",220,19.0,7.0,13.0,2.0,1.0,400,220,"1 pie",None,True,["gluten","dairy"],["pot pie","potpie"],"generic"),
 ("guacamole","Guacamole","mixed",150,8.5,2.0,13.0,0.7,6.0,260,60,"1/4 cup",None,False,[],["guacamole","avocado dip"],"generic"),
 ("consomme","Clear soup / consommé","mixed",7,0.4,1.2,0.0,0.4,0.0,300,240,"1 bowl",None,False,[],["consomme","clear soup","broth","soup"],"generic"),
 ("yogurt","Yogurt, plain low-fat","dairy",63,7.0,5.3,1.6,7.0,0.0,70,170,"1 cup",35,False,["dairy"],["yogurt","yoghurt"],"generic"),
 ("milk","Milk, whole","dairy",61,4.8,3.2,3.3,5.0,0.0,43,244,"1 cup",39,False,["dairy"],["milk"],"generic"),
 ("ice_cream","Ice cream, vanilla","dessert",207,24.0,3.5,11.0,21.0,0.7,80,66,"1 scoop",51,True,["dairy"],["ice cream"],"generic"),
 ("donut","Doughnut, glazed","dessert",421,51.3,5.6,22.9,21.0,1.2,330,60,"1 doughnut",76,True,["gluten","egg","dairy"],["donut","doughnut"],"generic"),
 ("chocolate_cake","Chocolate cake with frosting","dessert",367,55.0,4.0,16.0,37.0,1.8,334,95,"1 slice",38,True,["gluten","egg","dairy"],["cake","chocolate cake"],"generic"),
 ("trifle","Trifle","dessert",160,24.0,3.0,6.0,18.0,0.5,70,150,"1 cup",None,True,["gluten","egg","dairy"],["trifle"],"generic"),
 ("coffee_black","Coffee, black (no sugar)","beverage",2,0.0,0.3,0.0,0.0,0.0,2,240,"1 cup",None,False,[],["coffee","black coffee","kopi-o kosong","americano","espresso"],"generic"),
 ("cola","Soft drink, cola (sugar-sweetened)","beverage",42,10.6,0.0,0.0,10.6,0.0,4,330,"1 can",63,True,[],["coke","cola","soda","soft drink"],"generic"),
 ("orange_juice","Orange juice","beverage",45,10.4,0.7,0.2,8.4,0.2,1,248,"1 cup",50,False,[],["orange juice","oj","juice"],"generic"),
 ("red_wine","Red wine","beverage",85,2.6,0.1,0.0,0.6,0.0,4,150,"1 glass",None,False,[],["wine","red wine"],"generic"),
 ("eggnog","Eggnog","beverage",88,8.1,4.6,4.2,8.1,0.0,54,254,"1 cup",None,False,["egg","dairy"],["eggnog"],"generic"),
 ("water","Water","beverage",0,0.0,0.0,0.0,0.0,0.0,0,250,"1 glass",None,False,[],["water","plain water"],"generic"),
 # Singapore hawker dishes
 ("chicken_rice","Hainanese chicken rice","sg_dish",160,19.7,6.6,6.1,0.5,0.5,342,380,"1 plate",None,True,["soy"],["chicken rice","hainanese chicken rice"],"sg"),
 ("nasi_lemak","Nasi lemak (egg, ikan bilis, peanuts, sambal)","sg_dish",190,22.0,5.5,9.0,2.0,1.5,350,260,"1 plate",None,True,["peanut","egg","fish"],["nasi lemak"],"sg"),
 ("char_kway_teow","Char kway teow","sg_dish",194,23.0,5.5,9.5,2.5,1.0,500,384,"1 plate",None,True,["egg","shellfish","soy"],["char kway teow","ckt","fried kway teow"],"sg"),
 ("laksa","Laksa (curry noodle soup)","sg_dish",98,9.0,4.3,5.2,1.0,0.8,410,600,"1 bowl",None,True,["shellfish","fish"],["laksa","curry laksa"],"sg"),
 ("fish_soup_beehoon","Sliced fish bee hoon soup","sg_dish",54,6.0,4.0,1.6,0.3,0.3,300,650,"1 bowl",None,True,["fish"],["fish soup","fish bee hoon","sliced fish soup"],"sg"),
 ("roti_prata","Roti prata, plain","sg_dish",318,43.0,7.5,13.0,2.0,2.0,450,60,"1 piece",None,True,["gluten","dairy"],["prata","roti prata","roti canai"],"sg"),
 ("mee_goreng","Mee goreng","sg_dish",188,24.0,6.0,7.7,3.0,1.5,560,350,"1 plate",None,True,["gluten","egg","soy"],["mee goreng","fried noodles"],"sg"),
 ("nasi_goreng","Nasi goreng (fried rice)","sg_dish",175,24.0,5.5,6.5,1.5,1.0,450,330,"1 plate",None,True,["egg","soy"],["nasi goreng","fried rice"],"sg"),
 ("bak_chor_mee","Bak chor mee (dry)","sg_dish",170,20.0,8.0,6.5,1.5,1.0,600,300,"1 bowl",None,True,["gluten","soy"],["bak chor mee","minced meat noodles"],"sg"),
 ("wanton_mee","Wanton mee (dry)","sg_dish",136,18.0,6.5,4.0,1.5,0.8,520,300,"1 plate",None,True,["gluten","egg","soy"],["wanton mee","wonton noodles"],"sg"),
 ("hokkien_mee","Hokkien prawn mee","sg_dish",150,18.0,6.0,6.0,1.5,0.8,480,400,"1 plate",None,True,["shellfish","egg","gluten"],["hokkien mee","prawn mee"],"sg"),
 ("fried_carrot_cake","Fried carrot cake (chai tow kway, white)","sg_dish",190,23.0,4.0,9.0,1.0,0.8,520,300,"1 plate",None,True,["egg"],["carrot cake","chai tow kway"],"sg"),
 ("chicken_satay","Chicken satay with peanut sauce","sg_dish",230,6.0,22.0,13.0,5.0,1.0,480,100,"~6 sticks",None,False,["peanut"],["satay","chicken satay"],"sg"),
 ("kaya_toast","Kaya toast with butter","sg_dish",340,45.0,6.0,15.0,18.0,1.5,400,70,"1 set (2 slices)",None,True,["gluten","dairy","egg"],["kaya toast"],"sg"),
 ("popiah","Popiah (fresh spring roll)","sg_dish",145,20.0,4.0,5.0,4.0,2.0,380,130,"1 roll",None,False,["gluten","egg","peanut"],["popiah","spring roll"],"sg"),
 ("yong_tau_foo","Yong tau foo (soup)","sg_dish",60,5.0,4.0,2.5,1.0,0.8,330,550,"1 bowl",None,False,["soy","fish"],["yong tau foo","ytf"],"sg"),
 ("kopi","Kopi (coffee with condensed milk)","beverage",52,8.0,1.3,1.6,8.0,0.0,20,230,"1 cup",None,True,["dairy"],["kopi","kopi c","coffee with milk"],"sg"),
 ("teh_tarik","Teh tarik / teh (condensed milk)","beverage",55,9.0,1.4,1.5,9.0,0.0,22,230,"1 cup",None,True,["dairy"],["teh","teh tarik","milk tea"],"sg"),
 ("bubble_tea","Bubble milk tea with pearls","beverage",70,14.0,0.5,1.5,9.0,0.0,20,500,"1 regular cup",None,True,["dairy"],["bubble tea","boba","pearl milk tea"],"sg"),
 ("chendol","Chendol","dessert",160,27.0,1.5,5.5,20.0,1.0,40,300,"1 bowl",None,True,[],["chendol","cendol"],"sg"),
]

def main():
    foods = []
    for r in ROWS:
        (key, name, cat, kcal, carb, prot, fat, sugar, fiber, na, sg, sdesc, gi, refined, allergens, aliases, region) = r
        foods.append({
            "key": key, "name": name, "category": cat, "region": region,
            "per_100g": {"calories_kcal": kcal, "carbs_g": carb, "protein_g": prot, "fat_g": fat,
                          "sugar_g": sugar, "fiber_g": fiber, "sodium_mg": na},
            "default_serving_g": sg, "serving_desc": sdesc,
            "glycemic_index": gi, "gi_source": GI_SRC if gi is not None else None,
            "refined_carb": refined, "allergens": allergens, "aliases": aliases,
            "source": HPB if region == "sg" and cat in ("sg_dish", "beverage", "dessert") else USDA,
            "verification": "transcribed_unverified",
        })
    out = Path(__file__).with_name("foods.json")
    out.write_text(json.dumps({"version": "mvp-0.1", "foods": foods}, indent=1))
    print(f"wrote {len(foods)} foods -> {out}")

if __name__ == "__main__":
    main()
