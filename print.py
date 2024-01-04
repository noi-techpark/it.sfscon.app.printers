import os
import json
import PIL
import PIL.Image, PIL.ImageDraw

current_file_path = os.path.dirname(os.path.abspath(__file__))


def generate(r, fname='/tmp/label.png'):
    width = 700
    height = 480

    bckg = PIL.Image.new("1", (width, height), (255))

    sfsimg = PIL.Image.open(current_file_path + "/assets/sfs2023.png")

    sx = 0.85 * 0.23
    s = sfsimg.size
    s = (int(s[0] * sx), int(s[1] * sx))
    sfsimg = sfsimg.resize(s)

    img_draw = PIL.ImageDraw.Draw(bckg)

    fsize = 60

    from PIL import ImageFont

    font = ImageFont.truetype(current_file_path + "/assets/font-bold.ttf", fsize)
    font2 = ImageFont.truetype(current_file_path + "/assets/font.ttf", fsize)

    dname = r['first_name'] + ' ' + r['last_name']

    #    '''
    if len(dname) > 18:
        img_draw.text((32, 32), r['first_name'], fill='black', font=font, )
        img_draw.text((32, 118), r['last_name'], fill='black', font=font, )
        if 'organization' in r and r['organization']:
            img_draw.text((32, 184), r['organization'], fill='black', font=font2, )
    else:
        img_draw.text((32, 32), r['first_name'] + ' ' + r['last_name'], fill='black', font=font, )

        if 'organization' in r and r['organization']:
            img_draw.text((32, 118), r['organization'], fill='black', font=font2, )

        #    '''
    bckg.paste(sfsimg, (32, 350))

    px = PIL.Image.open(current_file_path + "/assets/1px.png")
    bckg.paste(px, (0, 0))
    bckg.paste(px, (699, 0))

    bckg.save(fname)

    return fname


def main():
    r = {
        "first_name": "NAME",
        "last_name": "SURNAME",
        "organization": "COMPANY NAME",
    }

    a = generate(r, fname='/tmp/label.png')
    print(a)

if __name__ == '__main__':
    main()
