import glob
from parse_pdfs import parse_madrid_ds

files = glob.glob("data/madrid/raw/pdf/*.pdf")
count_by_leg = {}
for f in files:
    votes = parse_madrid_ds(f)
    for v in votes:
        leg = v["id"].split("-")[1]
        count_by_leg[leg] = count_by_leg.get(leg, 0) + 1

print(count_by_leg)
