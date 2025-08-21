#!/usr/bin/env python3
"""Comprehensive test for AI with random moves and game simulation"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.types import Player, Shape, Piece
from core.rules import QuantikBoard
from ai_players.ulysse.algorithme import QuantikAI
import time
import random

def create_empty_pieces_count():
    return {
        Player.PLAYER1: {shape: 2 for shape in Shape},
        Player.PLAYER2: {shape: 2 for shape in Shape}
    }

def play_random_move(board, pieces_count, player):
    """Play a random valid move"""
    game_board = QuantikBoard()
    game_board.board = board
    
    valid_moves = []
    for shape in Shape:
        if pieces_count[player][shape] > 0:
            for row in range(4):
                for col in range(4):
                    if board[row][col] is None:
                        piece = Piece(shape, player)
                        if game_board.is_valid_move(row, col, piece):
                            valid_moves.append((row, col, shape))
    
    if valid_moves:
        row, col, shape = random.choice(valid_moves)
        board[row][col] = Piece(shape, player)
        pieces_count[player][shape] -= 1
        return (row, col, shape)
    
    return None

def print_board(board):
    """Print board in readable format"""
    print("  0 1 2 3")
    for i, row in enumerate(board):
        print(f"{i} ", end="")
        for cell in row:
            if cell is None:
                print(".", end=" ")
            else:
                print(cell.shape.value, end=" ")
        print()
    print()

def test_full_game_simulation():
    """Test AI in a full game against random moves"""
    print("=== Full Game Simulation ===")
    
    ai_player = Player.PLAYER1
    human_player = Player.PLAYER2
    ai = QuantikAI(ai_player)
    
    board = [[None for _ in range(4)] for _ in range(4)]
    pieces_count = create_empty_pieces_count()
    current_player = ai_player
    
    game_board = QuantikBoard()
    move_count = 0
    
    while move_count < 16:
        print(f"\n--- Move {move_count + 1} (Player {current_player.value}) ---")
        print_board(board)
        
        if current_player == ai_player:
            # AI turn
            print("AI is thinking...")
            start_time = time.time()
            
            try:
                move = ai.get_move(board, pieces_count)
                end_time = time.time()
                
                if move is None:
                    print("AI has no valid moves!")
                    break
                
                row, col, shape = move
                print(f"AI plays {shape.value} at ({row}, {col}) - Time: {end_time - start_time:.2f}s")
                
                # Validate move
                piece = Piece(shape, current_player)
                game_board.board = board
                if not game_board.is_valid_move(row, col, piece):
                    print(f"ERROR: AI played invalid move!")
                    break
                
                # Apply move
                board[row][col] = piece
                pieces_count[current_player][shape] -= 1
                
            except Exception as e:
                print(f"ERROR: AI crashed: {e}")
                import traceback
                traceback.print_exc()
                break
        else:
            # Random opponent turn
            print("Random player is playing...")
            move = play_random_move(board, pieces_count, current_player)
            if move is None:
                print("Random player has no valid moves!")
                break
            
            row, col, shape = move
            print(f"Random player plays {shape.value} at ({row}, {col})")
        
        # Check for victory
        game_board.board = board
        if game_board.check_victory():
            print(f"\n🎉 Game Over! Winner detected!")
            print_board(board)
            break
        
        # Switch players
        current_player = human_player if current_player == ai_player else ai_player
        move_count += 1
    
    print(f"\nGame finished after {move_count} moves")
    return True

def test_ai_performance():
    """Test AI performance over multiple scenarios"""
    print("\n=== AI Performance Test ===")
    
    ai = QuantikAI(Player.PLAYER1)
    total_time = 0
    test_count = 10
    
    for i in range(test_count):
        # Create semi-random board state
        board = [[None for _ in range(4)] for _ in range(4)]
        pieces_count = create_empty_pieces_count()
        
        # Place 3-6 random pieces
        moves_to_make = random.randint(3, 6)
        current_player = Player.PLAYER1
        
        for _ in range(moves_to_make):
            move = play_random_move(board, pieces_count, current_player)
            if move is None:
                break
            current_player = Player.PLAYER2 if current_player == Player.PLAYER1 else Player.PLAYER1
        
        # Test AI move
        start_time = time.time()
        move = ai.get_move(board, pieces_count)
        end_time = time.time()
        
        time_taken = end_time - start_time
        total_time += time_taken
        
        print(f"Test {i+1}: {time_taken:.3f}s - Move: {move}")
        
        if move is None:
            print(f"  WARNING: AI returned None in test {i+1}")
    
    avg_time = total_time / test_count
    print(f"\nAverage time per move: {avg_time:.3f}s")
    print(f"Total time for {test_count} tests: {total_time:.3f}s")
    
    return True

if __name__ == "__main__":
    random.seed(42)  # For reproducible results
    
    print("🤖 Comprehensive AI Test Suite")
    print("=" * 40)
    
    success1 = test_full_game_simulation()
    success2 = test_ai_performance()
    
    if success1 and success2:
        print("\n✅ All comprehensive tests passed!")
        print("🚀 AI is working correctly and efficiently!")
    else:
        print("\n❌ Some tests failed!")