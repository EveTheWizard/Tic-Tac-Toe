#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
It's a server for Tic Tac Toe game.
It will listen for incoming connections (via socket) on some port,
and then will communicate with client to emulate a game with artificial intelligence.

Usecase: run it on machine with internet. Setup it's IP in the tic_tac_common.py file,
thus a client would connect to the server.

---

# Game protocol description

## communication (send|recv)
1 step (server's or client's)
2 step check status
3 winner result

## how
all communication --- a JSON messages
Fields overview:
{ "step"  : [row, col] (indexies, from zero)
, "winner": 0|1|2	| 0 - nobody win yet. 1 - first. 2 - second. 3 - tie
, "error" : false|true
}

every time communication should contain all fields

---

"""

from __future__ import print_function
import tic_tac_common as ttc

import socket
import sys,  time
import json, random, copy, argparse

# ---------------------------------------------------------------------------- #

# if 1, a server-user will be asked about turn
MULTIPLAYER_MODE=1

# ---------------------------------------------------------------------------- #


def main():

	s = get_server_socket()

	try:
		### endless loop, for multiple linear games
		while True:

			print ('Waiting for a player...')
			(clientsocket, address) = s.accept() # blocking line
			print ('New player came from {0}\n'.format(address))
			clientsocket.sendall("Tic Tac Toe server greeting you!\nYou are Welcome!")

			gf = copy.deepcopy(ttc.GAME_FIELD)

			### one game, loop until winner or disconnect
			while True:


				#B get user's turn
				try:
					print("Wait for user's turn...")
					user_step = ttc.get_msg_from_socket(clientsocket, exception=True, ex=False)
				except Exception as exp:
					ttc.d(exp)
					ttc.d("\n" + 40*"=" + "\n")
					break;


				# validate step #
				step_check = {}

				ttc.d("user raw turn: {}".format(user_step))
				#user_turn_json_index = ttc.convert_json_turn_human_to_machine(user_step)
				#ttc.d("user turn in term of indexes: {}".format(user_turn_json_index))

				# thus, if True -> error = False
				step_check["error"] = not ttc.is_step_correct(user_step, gf) 


				if not step_check["error"]:
					ttc.apply_turn(user_step, gf, ttc.USER_RAW_STEP)
					step_check["winner"] = get_winner(gf)
					ttc.print_game_field(gf)
				else:
					step_check["winner"] = 0


				#B answer, is step correct #
				step_check_str = json.dumps(step_check)
				ttc.d("I will send: {0}".format(step_check_str))
				clientsocket.sendall(step_check_str)
				time.sleep(0.1)


				# if an error occured earlier -- get new answer from user
				if True == step_check["error"] or 0 != step_check["winner"]:
					continue;

				# do server step #
				ttc.d("proceed server turn")

				server_step_dict = do_server_step(gf)
				ttc.d("server step: {}".format(server_step_dict))
				ttc.apply_turn(json.dumps(server_step_dict), gf, ttc.SERVER_RAW_STEP)



				# check for winners
				server_step_dict["winner"] = get_winner(gf)
				server_step_dict["error"]  = False


				#B send server turn with winner result
				clientsocket.sendall( json.dumps(server_step_dict) )


				ttc.print_game_field(gf)


	except KeyboardInterrupt as exp:
		print ("\nShutting down... {0}".format(exp))
	except Exception as exp:
		print("Sorry, but: {0}".format(exp))
	except:
		print("Unexpected error:", sys.exc_info()[0])



	try:
		clientsocket.close()
		s.close()
	except Exception as exp:
		# not an error on most cases
		ttc.d("may be you will be interested, but {0}".format(exp))

	sys.exit(0)





# ---------------------------------------------------------------------------- #
# -------------------- H E L P E R S ----------------------------------------- #
# ---------------------------------------------------------------------------- #

def get_server_socket ():
	"""
	Create server socket and bind it to port and listen for incoming connections
	"""

	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		my_hostname = socket.gethostname()
		s.bind((my_hostname, ttc.SERVER_PORT))
		# allow max 1 connection at time
		s.listen(1)
		print("Server runs on {0}:{1}\n".format(my_hostname, ttc.SERVER_PORT))
		return s
	except Exception as exp:
		print("Can't init socket on {0}:{1}".format(ttc.SERVER_IP, ttc.SERVER_PORT))
		print("~> %s" %exp)
		sys.exit(1)



# ---------------------------------------------------------------------------- #
# ---------------------------- L O G I C ------------------------------------- #
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
def it_is_first_server_turn (game_field):
	"""
	Check on @game_field, has a user already done the turn,
	and now it's first time, when the server should do his turn.

	@return:
		True  : yes, it's server first time after user
		False : no, it's some other situation
	"""

	count = 0

	for line in game_field:
		count += line.count(ttc.EMPTY_RAW_STEP)

	if count == 8:
		return True
	else:
		return False

# --------------------------------------------------------------------------- #

def has_line_with_two_moves(game_field, move_kind):
	"""
	Look in @game_field for lines with two cell with @move_kind

	@return
		list: [ True|False, [row, col] ]
		if list[0] is True, : such line exists, coodinates are in list[1]
		if list[0] is False : no, sorry - no list[1] possible.
		
	"""

	gf = game_field
	length = len(game_field)


	# check all rows and cols
	
	for j in range(length):
		# get row and col as lists
		row = [ gf[j][i] for i in range(length) ]
		col = [ gf[i][j] for i in range(length) ]

		if row.count(move_kind) == 2 and row.count(ttc.EMPTY_RAW_STEP) == 1:
			return [True, [j, row.index(ttc.EMPTY_RAW_STEP)] ]

		if col.count(move_kind) == 2 and col.count(ttc.EMPTY_RAW_STEP) == 1:
			#ttc.d("enemy col: j:{}, index of empty:".format(j, .index(ttc.EMPTY_RAW_STEP), j) )
			return [True, [col.index(ttc.EMPTY_RAW_STEP), j] ]


	# check diagonals
	diag_1 = [ gf[0][0], gf[1][1], gf[2][2] ]
	if diag_1.count(move_kind) == 2 and diag_1.count(ttc.EMPTY_RAW_STEP) == 1:
		i = diag_1.index(ttc.EMPTY_RAW_STEP)
		return [ True, [i, i] ]

	diag_2 = [ gf[2][0], gf[1][1], gf[0][2] ]
	if diag_2.count(move_kind) == 2 and diag_2.count(ttc.EMPTY_RAW_STEP) == 1:
		j = diag_2.index(ttc.EMPTY_RAW_STEP)
		i = -j + 2
		return [ True, [i, j] ]

	# oh no =\
	return [ False, [-1, -1] ]


# --------------------------------------------------------------------------- #

def do_server_step (game_field):
	"""
	Analyze situations on @game_field
	and try to do a step.

	or ask a user about the turn, if it is a multiplayer mode.

	@return
		dict in json format with field 'step':[int, int]
	"""
	tmp = {}

	"""
	if MULTIPLAYER_MODE == 1:
		tmp_str = ttc.get_turn_from_user (game_field)
		ttc.d("Your step is : {}".format(tmp_str))

		tmp = json.loads(tmp_str)

	else:
		# generally, good to check, that empty sections on @game_field even exist
	"""



	# ???????? ???????????? ??????, ???? ?????? ?????? ???????????????????????? ???????? #

	cell=()
	if it_is_first_server_turn(game_field):
		i = 0
		for line in game_field:
			if 0 != line.count( ttc.USER_RAW_STEP ):
				cell = ( i, line.index(ttc.USER_RAW_STEP) )
			i += 1

		ttc.d("How server see the cell of user first turn {0}".format(cell))

		if cell==(0,0) or cell==(0,2) or cell==(2,0) or cell==(2,2):
			tmp["step"] = [1, 1]
		else:
			tmp["step"] = [0, 0]

		return tmp


	# ???????? ???? ?????????? ?????? ???????? -- ?????????????????? #
	has_line_with_2_friendly_cells = has_line_with_two_moves(game_field, ttc.SERVER_RAW_STEP)
	if has_line_with_2_friendly_cells[0]:
		tmp["step"] = has_line_with_2_friendly_cells[1]
		ttc.d("step 2 attack {0}".format(tmp["step"]))
		return tmp


	# ???????? ???? ?????????? ?????? ?????????? -- ?????????????????? #
	has_line_with_2_enemy_cell = has_line_with_two_moves(game_field, ttc.USER_RAW_STEP)
	if has_line_with_2_enemy_cell[0]:
		tmp["step"] = has_line_with_2_enemy_cell[1]
		ttc.d("step 2 def {0}".format(tmp["step"]))
		return tmp





	# ?????????? - ????????????????????????????????????????????!

	random.seed()
	tmp["step"] = [random.randrange(3), random.randrange(3)]

	while True:
		tmp_json_str = json.dumps(tmp)
		ttc.d("server step: {0}".format(tmp_json_str))
		if not ttc.is_step_correct(tmp_json_str, game_field):
			tmp["step"] = [random.randrange(3), random.randrange(3)]
			continue
		else:
			break

	return tmp
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #

def get_winner (game_field):
	"""
	Analyze game (@game_field) and check, if a Winner exist.

	Return
		0 : nobody
		1 : user one (server | zero  | 5)
		2 : user two (client | cross | 2)
		3 : tie (no more free space)
	"""

	winner = 0
	gf = game_field  # weak reference

	empty = ttc.EMPTY_RAW_STEP	# 1
	cross = ttc.USER_RAW_STEP 	# 2
	zeros  = ttc.SERVER_RAW_STEP	# 5

	length = len(game_field)


	try:
		### check for a winner

		# by rows and cols...
		for j in range(length):
			row = [ gf[j][i] for i in range(length) ]
			col = [ gf[i][j] for i in range(length) ]
			if col.count(cross) == length or row.count(cross) == length:
				winner = 2
				raise Exception("User wins!")
			elif col.count(zeros) == length or row.count(zeros) == length:
				winner = 1
				raise Exception("Server wins!")


		# by diagonals
		for diag in [ [gf[0][0], gf[1][1], gf[2][2]], [gf[0][2], gf[1][1], gf[2][0]] ]:
			if diag.count(cross) == length:
				winner = 2
				raise Exception("User wins!")
			elif diag.count(zeros) == length:
				winner = 1
				raise Exception("Server wins!")


		### check for tie, by counting empty cells on every line
		empty_count = 0
		for line in game_field:
			empty_count += line.count(empty)
		if 0 == empty_count:
			winner = 3
			raise Exception("TIE! no more free space")


	except Exception as ex:
		# do nothing, just goto
		ttc.d(ex)


	return winner




# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
	# insert some help here

	parser = argparse.ArgumentParser(description='Run a server for Tic-Tac-toe client-server game.')

	parser.add_argument('-p', '--port', help='specify a port, on which listen for new connections',
						type=int)
	parser.add_argument('--debug', help='show debug output', action='store_true')

	parser.add_argument('-m', '--multiplayer', help='YOU want to play with user',
						action='store_true')

	args = parser.parse_args()

	if args.debug:
		ttc.DEBUG = 1
		print("Debug output: On")

	if args.port is not None:
		ttc.SERVER_PORT = args.port

	if args.multiplayer:
		MULTIPLAYER_MODE = 1
		print("Multiplayer mode: On. Autopilot is switched off.")


	main()
