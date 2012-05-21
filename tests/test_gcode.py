import os
import sys
lib_path = os.path.abspath('../')
sys.path.append(lib_path)

import glob
import unittest

import s3g

class ExtractCommentsTests(unittest.TestCase):
  def test_empty_string(self):
    line = ''
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert '' == comment

  def test_semicolon_only(self):
    line = ';'
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert '' == comment
    
  def test_semicolon_with_data(self):
    line = ';;asdf'
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert ';asdf' == comment

  def test_parens_after_semicolon_ignored(self):
    line = ';)))'
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert ')))' == comment

  def test_right_paren_only(self):
    line = '('
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert '' == comment

  def test_right_paren_with_comment(self):
    line = '(comment'
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert 'comment' == comment

  def test_command_left_paren(self):
    line = 'command)'
    self.assertRaises(s3g.CommentError, s3g.ExtractComments, line)

  def test_closed_parens(self):
    line = '()'
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert '' == comment
 
  def test_closed_parens_with_nested_parens(self):
    line = '(())'
    [command, comment] = s3g.ExtractComments(line)
    assert '' == command
    assert '' == comment

  def test_command_closed_parens_with_comment(self):
    line = 'commanda(comment)commandb'

    [command, comment] = s3g.ExtractComments(line)
    assert 'commandacommandb' == command
    assert 'comment' == comment

  def test_comment_left_and_semicolon(self):
    line = 'asdf(qwer);testing'
    [command, comment] = s3g.ExtractComments(line)
    self.assertEqual('asdf', command)
    self.assertEqual('testingqwer', comment)

class ParseCommandTests(unittest.TestCase):
  def test_empty_string(self):
    command = ''

    registers = s3g.ParseCommand(command)
    assert {} == registers

  def test_garbage_code(self):
    cases = [
      '1',
      '~',
    ]

    for command in cases:
      self.assertRaises(s3g.InvalidCodeError, s3g.ParseCommand, command)

  def test_single_code_garbage_value(self):
    cases = [
      'Ga',
      'G1a',
      'G12345a',
      'G1..0',
      'G1,0',
    ]

    for command in cases:
      self.assertRaises(ValueError, s3g.ParseCommand, command)

  def test_single_code_accepts_lowercase(self):
    command = 'g'
    expected_registers = {'G' : True}

    registers = s3g.ParseCommand(command)
    assert expected_registers == registers

  def test_single_code_no_value(self):
    command = 'G'
    expected_registers = {'G' : True}

    registers = s3g.ParseCommand(command)
    assert expected_registers == registers

  def test_single_code_with_value(self):
    command = 'G0'
    expected_registers = {'G' : 0}

    registers = s3g.ParseCommand(command)
    assert expected_registers == registers

  def test_single_code_leading_whitespace(self):
    command = '\t\t\t G0'
    expected_registers = {'G' : 0}

    registers = s3g.ParseCommand(command)
    assert expected_registers == registers

  def test_repeated_code(self):
    command = 'G0 G0'
    self.assertRaises(s3g.RepeatCodeError, s3g.ParseCommand, command)

  def test_reject_both_g_and_m_code(self):
    command = 'G0 M0'
    self.assertRaises(s3g.MultipleCommandCodeError, s3g.ParseCommand, command)

  def test_reject_both_g_and_m_code(self):
    command = 'M0 G0'
    self.assertRaises(s3g.MultipleCommandCodeError, s3g.ParseCommand, command)

  def test_many_codes(self):
    command = 'M0 X1 Y2 Z3 F4'
    expected_registers = {
      'M' : 0,
      'X' : 1,
      'Y' : 2,
      'Z' : 3,
      'F' : 4,
    }

    registers = s3g.ParseCommand(command)
    assert expected_registers == registers


class StateMachineTests(unittest.TestCase):
  def setUp(self):
    self.sm = s3g.GcodeStateMachine()

  def tearDown(self):
    self.sm = None

  def test_set_position(self):
    setPos = {
        'X' : 1,
        'Y' : 2,
        'Z' : 3,
        'A' : 4,
        'B' : 5,
        }
    self.sm.SetPosition(setPos)
    self.assertEqual(setPos, self.sm.position)

  def test_g1_state(self):
    command = 'G1 X1 Y2 Z3 A4 B5'
    self.sm.ExecuteLine(command)
    self.assertEqual({'X':1,'Y':2,'Z':3,'A':4,'B':5}, self.sm.position)
 
  def test_g10_state(self):
    command = 'G10 X1 Y2 Z3 A4 B5 P1'
    self.sm.ExecuteLine(command)
    self.assertEqual(1, self.sm.offset_register)
    self.assertEqual({'X':1,'Y':2,'Z':3,'A':4,'B':5}, self.sm.position)

  def test_g54_state(self):
    command = 'G54'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.toolhead, 0)

  def test_g55_state(self):
    command = 'G55'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.toolhead, 1)

  def test_g92_state(self):
    command = 'G92 X1 Y2 Z3 A4 B5'
    self.sm.ExecuteLine(command)
    self.assertEqual({'X':1,'Y':2,'Z':3,'A':4,'B':5}, self.sm.position)

  def test_g161_state(self):
    command = 'G161 Z'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.position['Z'], 0)

  def test_g162_state(self):
    command = 'G162 X Y'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.position['X'], 0)
    self.assertEqual(self.sm.position['Y'], 0)

  def test_M101_state(self):
    command = 'M101'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.tool_enabled, True)
    self.assertEqual(self.sm.direction, True)

  def test_m102_state(self):
    command = 'M102'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.tool_enabled, True)
    self.assertEqual(self.sm.direction, False)

  def test_m103_state(self):
    command = 'M103'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.tool_enabled, False)

  def test_m108_state(self):
    command = 'M108 R42'
    self.sm.ExecuteLine(command)
    self.assertEqual(self.sm.tool_speed, 42)

  def test_m132_state(self):
    self.sm.HomePosition = {'X' : 3, 'Y' : 2, 'Z' : 1}
    command = 'M132 X Y Z'
    self.sm.ExecuteLine(command)
    for axis in ['X', 'Y', 'Z']:
      self.assertEqual(self.sm.HomePosition[axis], self.sm.position[axis])
    
class ParseSampleGcodeFileTests(unittest.TestCase):
  """
  Run the parser across all of the sample gcode files, to verify that no assertions
  are thrown
  """
  def test_parse_files(self):
    # Terriable hack, to support running from the root or test directory.
    files = []
    path = '../doc/gcode_samples/'
    files += glob.glob(os.path.join(path, '*.gcode'))
    path = 'doc/gcode_samples/'
    files += glob.glob(os.path.join(path, '*.gcode'))

    assert len(files) > 0

    for file in files:
      with open(file) as lines:
        for line in lines:
          registers, comment = s3g.ParseLine(line)

  
if __name__ == "__main__":
  unittest.main()
