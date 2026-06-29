import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../utils/validators.dart';

class SmilesInput extends StatefulWidget {
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final String? hintText;
  final bool multiline;
  final int maxLines;

  const SmilesInput({
    super.key,
    this.controller,
    this.onChanged,
    this.hintText,
    this.multiline = false,
    this.maxLines = 1,
  });

  @override
  State<SmilesInput> createState() => _SmilesInputState();
}

class _SmilesInputState extends State<SmilesInput> {
  late final TextEditingController _controller;
  bool _isValid = false;
  String? _errorText;

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? TextEditingController();
    _controller.addListener(_validate);
  }

  void _validate() {
    final text = _controller.text;
    if (widget.multiline) {
      final smiles = Validators.parseMultiSmiles(text);
      setState(() {
        _isValid = smiles.isNotEmpty && smiles.every(Validators.isValidSmiles);
        _errorText = smiles.isEmpty ? 'Enter at least one SMILES' : null;
      });
    } else {
      final error = Validators.smilesError(text);
      setState(() {
        _isValid = error == null && text.isNotEmpty;
        _errorText = error;
      });
    }
    widget.onChanged?.call(text);
  }

  Future<void> _paste() async {
    final data = await Clipboard.getData(Clipboard.kTextPlain);
    if (data != null && data.text != null) {
      _controller.text = data.text!;
      _controller.selection = TextSelection.fromPosition(
        TextPosition(offset: _controller.text.length),
      );
    }
  }

  void _clear() {
    _controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Semantics(
      label: 'SMILES input field',
      child: TextField(
        controller: _controller,
        maxLines: widget.multiline ? widget.maxLines : 1,
        keyboardType: widget.multiline
            ? TextInputType.multiline
            : TextInputType.text,
        textInputAction: widget.multiline ? TextInputAction.newline : TextInputAction.done,
        autocorrect: false,
        enableSuggestions: false,
        decoration: InputDecoration(
          labelText: widget.multiline ? 'SMILES (one per line or comma-separated)' : 'SMILES',
          hintText: widget.hintText ??
              (widget.multiline ? 'CCO\nc1ccccc1\nCC(=O)O' : 'CCO'),
          errorText: _errorText,
          prefixIcon: Icon(
            Icons.science,
            color: _isValid ? Colors.green : theme.colorScheme.onSurface.withAlpha(150),
          ),
          suffixIcon: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.paste),
                tooltip: 'Paste from clipboard',
                onPressed: _paste,
              ),
              if (_controller.text.isNotEmpty)
                IconButton(
                  icon: const Icon(Icons.clear),
                  tooltip: 'Clear',
                  onPressed: _clear,
                ),
              if (_isValid)
                const Padding(
                  padding: EdgeInsets.only(right: 12),
                  child: Icon(Icons.check_circle, color: Colors.green),
                ),
            ],
          ),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(
              color: theme.colorScheme.outline.withAlpha(100),
            ),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(
              color: theme.colorScheme.primary,
              width: 2,
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    if (widget.controller == null) {
      _controller.dispose();
    }
    super.dispose();
  }
}
