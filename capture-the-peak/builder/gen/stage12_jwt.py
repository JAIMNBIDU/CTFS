"""CAMP 12 THE SUMMIT - JWT HS256 signed with a weak secret = the flag's inner text."""
import jwt
def build(ctx):
    inner = ctx.flag[len("acqu1redP34k{"):-1]   # you_reached_the_peak
    token = jwt.encode({"user": "climber", "role": "guest", "iss": "summit-beacon"},
                       inner, algorithm="HS256")
    ctx.write("token.txt", token + "\n")
    ctx.wordlist.add(inner)
